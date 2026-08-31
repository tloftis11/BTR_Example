"""
NAO (Nucleic Acid Observatory) / Environmental Metagenomics pipeline.

Source: NCBI SRA Project PRJNA729801 — SecureBio/NAO environmental metagenomics.
This project deposits wastewater metagenomics sequencing runs that are used to
detect novel pathogens from environmental samples.

Metric: number of sequencing runs submitted per week (proxy for surveillance activity).
When a run contains novel sequences, they appear as separate entries in the project.
"""

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

NCBI_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# NAO primary sampling locations (published in their papers)
NAO_SITES = [
    {"id": "nao_boston",    "name": "NAO — Deer Island (Boston)",  "lat": 42.340, "lon": -70.960},
    {"id": "nao_marin",     "name": "NAO — Marin County (CA)",     "lat": 37.960, "lon": -122.530},
    {"id": "nao_cambridge", "name": "NAO — Cambridge (MA)",        "lat": 42.374, "lon": -71.106},
    {"id": "nao_somerville","name": "NAO — Somerville (MA)",       "lat": 42.388, "lon": -71.100},
]


async def _get_run_ids(lookback_days: int) -> list[str]:
    """Search NCBI SRA for recent runs in the NAO project."""
    since = (date.today() - timedelta(days=lookback_days)).strftime("%Y/%m/%d")
    query = f"PRJNA729801[BioProject] AND {since}[Publication Date] : 3000[Publication Date]"
    params = {
        "db": "sra",
        "term": query,
        "retmax": 500,
        "retmode": "json",
        "usehistory": "y",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(NCBI_ESEARCH, params=params)
        resp.raise_for_status()
        data = resp.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids


async def _get_run_dates(ids: list[str]) -> list[dict]:
    """Fetch metadata for a batch of SRA runs to get their collection dates."""
    if not ids:
        return []
    params = {
        "db": "sra",
        "id": ",".join(ids[:200]),  # batch limit
        "retmode": "json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(NCBI_ESUMMARY, params=params)
        resp.raise_for_status()
        data = resp.json()

    result = data.get("result", {})
    runs = []
    for uid in result.get("uids", []):
        item = result.get(uid, {})
        # Try to extract a usable date
        pub_date = item.get("publishdate") or item.get("updatedate") or item.get("createdate") or ""
        runs.append({"uid": uid, "date": pub_date[:10] if pub_date else ""})
    return runs


async def fetch_nao(lookback_days: int = 365) -> int:
    """Pull NAO sequencing run counts from NCBI SRA and upsert weekly summaries."""
    try:
        run_ids = await _get_run_ids(lookback_days)
    except Exception as e:
        log.warning("NAO NCBI esearch failed: %s", e)
        return 0

    log.info("NAO: found %d SRA run IDs for PRJNA729801", len(run_ids))
    if not run_ids:
        return 0

    try:
        runs = await _get_run_dates(run_ids)
    except Exception as e:
        log.warning("NAO NCBI esummary failed: %s", e)
        return 0

    since = date.today() - timedelta(days=lookback_days)

    # Aggregate by week
    weekly_counts: dict[date, int] = {}
    for run in runs:
        try:
            d = date.fromisoformat(run["date"])
            if d < since:
                continue
            week = d - timedelta(days=d.weekday())
            weekly_counts[week] = weekly_counts.get(week, 0) + 1
        except Exception:
            continue

    if not weekly_counts:
        log.info("NAO: no dateable runs found")
        return 0

    # Fan out to all NAO sites (run count is the same per site — represents system activity)
    records = []
    for week_start, count in weekly_counts.items():
        for site in NAO_SITES:
            records.append({
                "source": "nao",
                "site_id": site["id"],
                "site_name": site["name"],
                "state": None,
                "county_fips": None,
                "lat": site["lat"],
                "lon": site["lon"],
                "pathogen": "Environmental Metagenome",
                "signal_date": week_start,
                "metric": "sequencing_runs",
                "value": float(count),
                "raw": {"ncbi_project": "PRJNA729801"},
            })

    # Deduplicate
    deduped: dict[tuple, dict] = {}
    for rec in records:
        key = (rec["source"], rec["site_id"], rec["signal_date"], rec["metric"], rec["pathogen"])
        deduped[key] = rec
    records = list(deduped.values())

    async with AsyncSessionLocal() as session:
        stmt = insert(Signal).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_signal",
            set_={"value": stmt.excluded.value, "raw": stmt.excluded.raw},
        )
        await session.execute(stmt)
        await session.commit()

    log.info("NAO: upserted %d weekly run-count records", len(records))
    return len(records)
