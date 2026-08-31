"""
SecureBio Detection (formerly Nucleic Acid Observatory) pipeline.

Data source: SecureBio public dashboard + NCBI SRA metadata
Dashboard:   https://securebio.org/detection
SRA project: PRJNA729801 (NAO wastewater metagenomics)

Current status: SecureBio does not yet publish a machine-readable API for their
novelty/signal scores. Their raw sequencing reads are deposited to NCBI SRA, and
summary data is shown on their public dashboard as rendered SVG/JSON.

This module:
  1. Attempts to fetch summary JSON from the SecureBio dashboard endpoint
     (reverse-engineered from their public dashboard network requests).
  2. Falls back to inserting static site-level metadata (no signal values)
     so the map always shows SecureBio site locations even without live data.

When SecureBio publishes a formal API, update SECUREBIO_API below.
"""

import logging
from datetime import date

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

SECUREBIO_API = "https://securebio.org/api/dashboard/sites"  # provisional

SBD_SITES = [
    {"id": "sbd_chicago",  "name": "SecureBio — Chicago",       "lat": 41.878, "lon": -87.635, "state": "IL"},
    {"id": "sbd_nyc",      "name": "SecureBio — New York City",  "lat": 40.730, "lon": -73.990, "state": "NY"},
    {"id": "sbd_la",       "name": "SecureBio — Los Angeles",    "lat": 34.022, "lon": -118.282,"state": "CA"},
    {"id": "sbd_boston",   "name": "SecureBio — Boston",         "lat": 42.320, "lon": -71.082, "state": "MA"},
    {"id": "sbd_houston",  "name": "SecureBio — Houston",        "lat": 29.758, "lon": -95.368, "state": "TX"},
    {"id": "sbd_miami",    "name": "SecureBio — Miami",          "lat": 25.774, "lon": -80.194, "state": "FL"},
    {"id": "sbd_seattle",  "name": "SecureBio — Seattle",        "lat": 47.606, "lon": -122.332,"state": "WA"},
    {"id": "sbd_denver",   "name": "SecureBio — Denver",         "lat": 39.739, "lon": -104.985,"state": "CO"},
    {"id": "sbd_stlouis",  "name": "SecureBio — St. Louis",      "lat": 38.627, "lon": -90.197, "state": "MO"},
    {"id": "sbd_phoenix",  "name": "SecureBio — Phoenix",        "lat": 33.448, "lon": -112.074,"state": "AZ"},
    {"id": "sbd_atlanta",  "name": "SecureBio — Atlanta",        "lat": 33.749, "lon": -84.388, "state": "GA"},
    {"id": "sbd_minneap",  "name": "SecureBio — Minneapolis",    "lat": 44.978, "lon": -93.265, "state": "MN"},
    {"id": "sbd_portland", "name": "SecureBio — Portland",       "lat": 45.523, "lon": -122.676,"state": "OR"},
]


async def fetch_securebio(lookback_days: int = 90) -> int:
    """
    Attempts live fetch from SecureBio dashboard; falls back to site-presence records.
    Returns number of rows upserted.
    """
    live_data = await _try_live_fetch()

    if live_data:
        return await _upsert_live(live_data)
    else:
        log.info("SecureBio: live API unavailable, inserting site-presence records")
        return await _upsert_sites_only()


async def _try_live_fetch() -> list[dict] | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(SECUREBIO_API)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        log.debug("SecureBio live fetch skipped: %s", e)
    return None


async def _upsert_live(data: list[dict]) -> int:
    records = []
    today = date.today()
    for row in data:
        site_id = row.get("site_id") or row.get("id")
        if not site_id:
            continue
        records.append({
            "source": "sbd",
            "site_id": f"sbd_{site_id}",
            "site_name": row.get("name"),
            "state": row.get("state"),
            "lat": row.get("lat"),
            "lon": row.get("lon"),
            "pathogen": "Novel/Unknown",
            "signal_date": today,
            "metric": "novelty_score",
            "value": row.get("novelty_score"),
            "raw": row,
        })
    return await _do_upsert(records)


async def _upsert_sites_only() -> int:
    today = date.today()
    records = [
        {
            "source": "sbd",
            "site_id": s["id"],
            "site_name": s["name"],
            "state": s["state"],
            "county_fips": None,
            "lat": s["lat"],
            "lon": s["lon"],
            "pathogen": "Novel/Unknown",
            "signal_date": today,
            "metric": "novelty_score",
            "value": None,
            "raw": {"note": "site_presence_only"},
        }
        for s in SBD_SITES
    ]
    return await _do_upsert(records)


async def _do_upsert(records: list[dict]) -> int:
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
    return len(records)
