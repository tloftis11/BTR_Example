"""
Nextstrain novel pathogen genomics pipeline.

Fetches open phylogenetic datasets from Nextstrain for high-consequence pathogens:
  - H5N1 avian influenza (HPAI) — current pandemic preparedness concern
  - Mpox (monkeypox) — multi-country outbreak tracking

Parses the phylogenetic tree JSON to extract sequence counts by country and week.
Metric: number of publicly deposited sequences per country per week, which
reflects both surveillance intensity and active transmission.
"""

import logging
from datetime import date, timedelta, datetime
from collections import defaultdict

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

NEXTSTRAIN_BASE = "https://nextstrain.org/charon/getDataset"

# (prefix, source_label, metric_name, pathogen_name)
DATASETS = [
    ("/avian-flu/h5n1/ha/all-time", "H5N1", "h5n1_sequences", "H5N1 Avian Influenza"),
    ("/mpox/all-clades",             "mpox", "mpox_sequences",  "Mpox"),
]

# Fallback candidate prefixes to try for the mpox dataset
MPOX_FALLBACK_PREFIXES = [
    "/mpox/all-clades",
    "/mpox/mpxv",
    "/mpox/clade-iib",
    "/mpox/global",
]

# Country centroids for Nextstrain country labels
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "USA": (37.1, -95.7), "United States": (37.1, -95.7),
    "China": (35.9, 104.2), "Japan": (36.2, 138.3),
    "Cambodia": (12.6, 104.9), "Vietnam": (14.1, 108.3),
    "Indonesia": (-0.8, 113.9), "India": (20.6, 78.9),
    "Bangladesh": (23.7, 90.4), "Egypt": (26.8, 30.8),
    "Nigeria": (9.1, 8.7), "Ghana": (7.9, -1.0),
    "Democratic Republic of the Congo": (-4.0, 21.8),
    "Uganda": (1.4, 32.3), "Ethiopia": (9.1, 40.5),
    "South Africa": (-30.6, 22.9), "Kenya": (-0.0, 37.9),
    "Brazil": (-14.2, -51.9), "Peru": (-9.2, -75.0),
    "Colombia": (4.6, -74.1), "Mexico": (23.6, -102.6),
    "United Kingdom": (55.4, -3.4), "France": (46.2, 2.2),
    "Germany": (51.2, 10.5), "Spain": (40.5, -3.7),
    "Italy": (41.9, 12.6), "Netherlands": (52.1, 5.3),
    "Belgium": (50.5, 4.5), "Canada": (56.1, -106.3),
    "Australia": (-25.3, 133.8), "Russia": (61.5, 105.3),
    "Iran": (32.4, 53.7), "Pakistan": (30.4, 69.3),
    "Nepal": (28.4, 84.1), "South Korea": (35.9, 127.8),
    "Philippines": (12.9, 121.8), "Thailand": (15.9, 100.9),
    "Myanmar": (21.9, 95.9), "Malaysia": (4.2, 101.9),
    "Taiwan": (23.7, 121.0), "Austria": (47.5, 14.6),
    "Switzerland": (46.8, 8.2), "Sweden": (62.2, 17.6),
    "Denmark": (56.3, 9.5), "Norway": (60.5, 8.5),
    "Poland": (52.1, 19.1), "Ukraine": (48.4, 31.2),
    "Turkey": (38.9, 35.2), "Israel": (31.0, 34.9),
    "Saudi Arabia": (23.9, 45.1), "UAE": (24.0, 54.0),
    "Qatar": (25.4, 51.2), "Kuwait": (29.3, 47.7),
    "Morocco": (31.8, -7.1), "Tunisia": (33.9, 9.6),
    "Algeria": (28.0, 2.6), "Libya": (26.3, 17.2),
    "Sudan": (12.9, 30.2), "Somalia": (5.2, 46.2),
    "Cameroon": (3.9, 11.5), "Senegal": (14.5, -14.5),
    "Unknown": (20.0, 0.0),
}


def _num_date_to_date(num_date: float) -> date:
    """Convert Nextstrain numeric date (e.g. 2024.5) to a date object."""
    year = int(num_date)
    day_of_year = int((num_date - year) * (366 if year % 4 == 0 else 365))
    return date(year, 1, 1) + timedelta(days=day_of_year)


def _walk_tips(node: dict, tips: list) -> None:
    """Recursively collect leaf node attributes from a Nextstrain tree."""
    children = node.get("children")
    if children:
        for child in children:
            _walk_tips(child, tips)
    else:
        attrs = node.get("node_attrs", {})
        country_val = attrs.get("country", {}).get("value")
        num_date = attrs.get("num_date", {}).get("value")
        if country_val and num_date is not None:
            tips.append({"country": country_val, "num_date": float(num_date)})


async def _fetch_dataset(prefix: str | list[str]) -> tuple[str | None, list[dict] | None]:
    """Try one prefix (or a list of fallback prefixes). Returns (used_prefix, tips)."""
    prefixes = [prefix] if isinstance(prefix, str) else prefix

    async with httpx.AsyncClient(timeout=60) as client:
        for p in prefixes:
            try:
                resp = await client.get(
                    NEXTSTRAIN_BASE,
                    params={"prefix": p},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code != 200:
                    log.debug("Nextstrain %s: HTTP %s", p, resp.status_code)
                    continue
                data = resp.json()
                tree = data.get("tree")
                if not tree:
                    log.debug("Nextstrain %s: no tree in response", p)
                    continue
                tips: list[dict] = []
                _walk_tips(tree, tips)
                log.info("Nextstrain %s: extracted %d tip sequences", p, len(tips))
                return p, tips
            except Exception as e:
                log.debug("Nextstrain %s fetch failed: %s", p, e)

    log.warning("Nextstrain: all candidates failed for %s", prefixes[0])
    return None, None


async def fetch_nextstrain(lookback_days: int = 365) -> int:
    """Pull Nextstrain H5N1 and mpox datasets and upsert sequence counts."""
    since = date.today() - timedelta(days=lookback_days)
    total_rows = 0

    for prefix_or_label, label, metric, pathogen in DATASETS:
        candidates = MPOX_FALLBACK_PREFIXES if label == "mpox" else [prefix_or_label]
        used_prefix, tips = await _fetch_dataset(candidates)
        if not tips:
            continue

        # Aggregate: count sequences by (country, week_start)
        weekly: dict[tuple[str, date], int] = defaultdict(int)
        for tip in tips:
            try:
                seq_date = _num_date_to_date(tip["num_date"])
                if seq_date < since:
                    continue
                week_start = seq_date - timedelta(days=seq_date.weekday())
                country = tip["country"]
                weekly[(country, week_start)] += 1
            except Exception:
                continue

        if not weekly:
            continue

        records = []
        for (country, week_start), count in weekly.items():
            coords = COUNTRY_COORDS.get(country, COUNTRY_COORDS["Unknown"])
            site_id = f"nst_{label}_{country.lower()[:20].replace(' ', '_')}"
            records.append({
                "source": "nst",
                "site_id": site_id,
                "site_name": f"{label} — {country}",
                "state": None,
                "county_fips": None,
                "lat": coords[0],
                "lon": coords[1],
                "pathogen": pathogen,
                "signal_date": week_start,
                "metric": metric,
                "value": float(count),
                "raw": {"country": country, "dataset": used_prefix},
            })

        # Deduplicate
        deduped: dict[tuple, dict] = {}
        for rec in records:
            key = (rec["source"], rec["site_id"], rec["signal_date"], rec["metric"], rec["pathogen"])
            deduped[key] = rec
        records = list(deduped.values())

        if not records:
            continue

        async with AsyncSessionLocal() as session:
            stmt = insert(Signal).values(records)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_signal",
                set_={"value": stmt.excluded.value, "raw": stmt.excluded.raw},
            )
            await session.execute(stmt)
            await session.commit()

        log.info("Nextstrain %s: upserted %d records", label, len(records))
        total_rows += len(records)

    return total_rows
