"""
TGS (Traveler Genomic Surveillance) / CDC Variant Proportions pipeline.

Primary source: CDC SARS-CoV-2 Variant Proportions
Endpoint:       https://data.cdc.gov/resource/jr58-6ysp.json
Cadence:        Weekly

Note on TGS specifics: CDC's public TGS Nowcast data (variant proportions from
airport travelers) is published weekly as aggregate national/regional figures.
When a dedicated TGS endpoint with airport-level resolution becomes available
via data.cdc.gov, update VARIANTS_API and the field mapping below.

Secondary source: CDC Influenza Surveillance (FluView)
Endpoint:        https://data.cdc.gov/resource/jhax-xkrj.json
"""

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

VARIANTS_API = f"https://data.cdc.gov/resource/jr58-6ysp.json"

# Major US international airports used as proxy "TGS sites"
TGS_AIRPORTS = [
    {"id": "tgs_ORD", "name": "Chicago O'Hare (ORD)",       "lat": 41.978, "lon": -87.907, "state": "IL"},
    {"id": "tgs_JFK", "name": "New York JFK",                "lat": 40.641, "lon": -73.779, "state": "NY"},
    {"id": "tgs_LAX", "name": "Los Angeles (LAX)",           "lat": 33.943, "lon": -118.408,"state": "CA"},
    {"id": "tgs_MIA", "name": "Miami International (MIA)",   "lat": 25.796, "lon": -80.287, "state": "FL"},
    {"id": "tgs_SFO", "name": "San Francisco (SFO)",         "lat": 37.621, "lon": -122.379,"state": "CA"},
    {"id": "tgs_ATL", "name": "Hartsfield-Jackson (ATL)",    "lat": 33.641, "lon": -84.428, "state": "GA"},
    {"id": "tgs_IAD", "name": "Washington Dulles (IAD)",     "lat": 38.944, "lon": -77.456, "state": "VA"},
    {"id": "tgs_BOS", "name": "Boston Logan (BOS)",          "lat": 42.365, "lon": -71.011, "state": "MA"},
]


async def fetch_tgs(lookback_days: int = 90) -> int:
    since = (date.today() - timedelta(days=lookback_days)).isoformat()

    params = {
        "$where": f"week_ending >= '{since}'",
        "$limit": 10000,
        "$order": "week_ending ASC",
        # No $select — fetch all columns to avoid 400s if CDC renames fields.
    }
    if settings.socrata_app_token:
        params["$$app_token"] = settings.socrata_app_token

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(VARIANTS_API, params=params)
            resp.raise_for_status()
            rows = resp.json()
    except httpx.HTTPError as e:
        log.warning("TGS variant fetch failed: %s", e)
        return 0

    log.info("TGS variants: fetched %d rows", len(rows))

    # Aggregate national-level (usa_or_hhsregion == "USA") variant shares
    national = [r for r in rows if r.get("usa_or_hhsregion", "").upper() == "USA"]

    records = []
    for r in national:
        try:
            signal_date = date.fromisoformat(r["week_ending"][:10])
        except (KeyError, ValueError):
            continue

        variant = r.get("variant") or r.get("lineage") or "Unknown"
        share = None
        for field in ("share", "proportion", "modelestimate", "weighted_estimate"):
            try:
                share = float(r[field])
                break
            except (KeyError, TypeError, ValueError):
                continue

        # Write one record per airport so the map has geographic points
        for airport in TGS_AIRPORTS:
            records.append({
                "source": "tgs",
                "site_id": airport["id"],
                "site_name": airport["name"],
                "state": airport["state"],
                "county_fips": None,
                "lat": airport["lat"],
                "lon": airport["lon"],
                "pathogen": f"SARS-CoV-2 / {variant}",
                "signal_date": signal_date,
                "metric": "variant_proportion",
                "value": share,
                "raw": {"variant": variant, "region": r.get("usa_or_hhsregion")},
            })

    # Deduplicate by constraint key — CDC may return multiple rows for the same
    # (week_ending, variant, USA) which fan out to duplicate airport records.
    deduped: dict[tuple, dict] = {}
    for rec in records:
        key = (rec["source"], rec["site_id"], rec["signal_date"], rec["metric"], rec["pathogen"])
        deduped[key] = rec
    records = list(deduped.values())

    if not records:
        return 0

    async with AsyncSessionLocal() as session:
        stmt = insert(Signal).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_signal",
            set_={"value": stmt.excluded.value, "raw": stmt.excluded.raw},
        )
        await session.execute(stmt)
        await session.commit()

    log.info("TGS: upserted %d signal rows", len(records))
    return len(records)
