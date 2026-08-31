"""
NWSS (National Wastewater Surveillance System) pipeline.

Data source: CDC Open Data / Socrata
Dataset:     NWSS Public SARS-CoV-2 Wastewater Metric Data
Endpoint:    https://data.cdc.gov/resource/2ew6-ywp6.json
Cadence:     Weekly (updated each Friday)
Docs:        https://data.cdc.gov/Public-Health-Surveillance/NWSS-Public-SARS-CoV-2-Wastewater-Metric-Data/2ew6-ywp6
"""

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Signal, PipelineRun

log = logging.getLogger(__name__)

# Approximate centroids for WWTP jurisdictions (state-level fallback)
STATE_CENTROIDS: dict[str, tuple[float, float]] = {
    "AL": (32.8, -86.8), "AK": (64.2, -153.4), "AZ": (34.3, -111.1),
    "AR": (34.8, -92.2), "CA": (37.2, -119.5), "CO": (39.0, -105.5),
    "CT": (41.6, -72.7), "DE": (38.9, -75.5),  "FL": (28.6, -81.5),
    "GA": (32.7, -83.4), "HI": (20.3, -156.4), "ID": (44.4, -114.6),
    "IL": (40.0, -89.2), "IN": (39.8, -86.1),  "IA": (42.1, -93.2),
    "KS": (38.5, -98.4), "KY": (37.5, -85.3),  "LA": (31.2, -92.1),
    "ME": (45.4, -69.0), "MD": (39.0, -76.8),  "MA": (42.3, -71.8),
    "MI": (44.3, -85.4), "MN": (46.4, -93.1),  "MS": (32.7, -89.7),
    "MO": (38.4, -92.5), "MT": (47.0, -110.0), "NE": (41.5, -99.9),
    "NV": (39.3, -116.6),"NH": (43.7, -71.6),  "NJ": (40.1, -74.5),
    "NM": (34.8, -106.2),"NY": (42.9, -75.6),  "NC": (35.6, -79.4),
    "ND": (47.5, -100.5),"OH": (40.4, -82.8),  "OK": (35.6, -97.5),
    "OR": (44.6, -122.1),"PA": (40.9, -77.8),  "RI": (41.7, -71.5),
    "SC": (33.9, -80.9), "SD": (44.4, -100.3), "TN": (35.9, -86.7),
    "TX": (31.5, -99.3), "UT": (39.3, -111.1), "VT": (44.0, -72.7),
    "VA": (37.8, -79.5), "WA": (47.4, -120.5), "WV": (38.6, -80.6),
    "WI": (44.5, -89.6), "WY": (43.0, -107.6), "DC": (38.9, -77.0),
    "PR": (18.2, -66.5),
}

NWSS_API = f"https://data.cdc.gov/resource/2ew6-ywp6.json"


async def fetch_nwss(lookback_days: int = 90) -> int:
    """Pull NWSS data and upsert into signals table. Returns rows inserted."""
    since = (date.today() - timedelta(days=lookback_days)).isoformat()

    params = {
        "$where": f"date_start >= '{since}'",
        "$limit": 50000,
        "$order": "date_start ASC",
        # No $select — fetch all columns so field-name changes in the dataset
        # don't cause 400 errors; we pick what we need from the response.
    }
    if settings.socrata_app_token:
        params["$$app_token"] = settings.socrata_app_token

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(NWSS_API, params=params)
        resp.raise_for_status()
        rows = resp.json()

    log.info("NWSS: fetched %d rows", len(rows))

    records = []
    for r in rows:
        wwtp_id = r.get("wwtp_id", "")
        if not wwtp_id:
            continue
        state = (r.get("wwtp_jurisdiction") or "").upper().strip()
        lat, lon = STATE_CENTROIDS.get(state, (None, None))

        try:
            signal_date = date.fromisoformat(r["date_start"][:10])
        except (KeyError, ValueError):
            continue

        def safe_float(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        records.append({
            "source": "nwss",
            "site_id": f"nwss_{wwtp_id}",
            "site_name": county_label(r),
            "state": state,
            "county_fips": r.get("county_fips"),
            "lat": lat,
            "lon": lon,
            "pathogen": "SARS-CoV-2",
            "signal_date": signal_date,
            "metric": "detect_prop_15d",
            "value": safe_float(r.get("detect_prop_15d")),
            "raw": {
                "ptc_15d": safe_float(r.get("ptc_15d")),
                "percentile": safe_float(r.get("percentile")),
                "population_served": r.get("population_served"),
            },
        })

        # Also store ptc_15d as a separate metric row
        ptc = safe_float(r.get("ptc_15d"))
        if ptc is not None:
            records.append({
                "source": "nwss",
                "site_id": f"nwss_{wwtp_id}",
                "site_name": county_label(r),
                "state": state,
                "county_fips": r.get("county_fips"),
                "lat": lat,
                "lon": lon,
                "pathogen": "SARS-CoV-2",
                "signal_date": signal_date,
                "metric": "ptc_15d",
                "value": ptc,
                "raw": None,
            })

    # Deduplicate by constraint key in case CDC returns duplicate rows.
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
        result = await session.execute(stmt)
        await session.commit()

    log.info("NWSS: upserted %d signal rows", len(records))
    return len(records)


def county_label(r: dict) -> str:
    names = r.get("county_names") or ""
    state = r.get("wwtp_jurisdiction") or ""
    if names:
        return f"{names}, {state}"
    return state
