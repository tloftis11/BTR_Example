"""
HealthMap global disease alert pipeline.

HealthMap (healthmap.org) aggregates disease events from ProMED, WHO, news,
and government sources using automated natural-language detection. This pipeline
pulls recent alerts and stores aggregated event intensity by location and week.
"""

import logging
import re
from datetime import date, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

HEALTHMAP_API = "https://www.healthmap.org/getAddedAlerts.php"

DISEASE_CATEGORIES = {
    "h5n1": "H5N1 Avian Influenza",
    "h5": "H5 Avian Influenza",
    "h7n9": "H7N9 Avian Influenza",
    "avian influenza": "Avian Influenza",
    "avian flu": "Avian Influenza",
    "mpox": "Mpox",
    "monkeypox": "Mpox",
    "ebola": "Ebola Virus Disease",
    "marburg": "Marburg Virus Disease",
    "lassa": "Lassa Fever",
    "plague": "Plague",
    "cholera": "Cholera",
    "dengue": "Dengue",
    "zika": "Zika",
    "covid-19": "COVID-19",
    "sars-cov-2": "COVID-19",
    "influenza": "Influenza",
    "unknown pneumonia": "Pneumonia (unknown etiology)",
    "pneumonia": "Pneumonia",
    "anthrax": "Anthrax",
    "botulism": "Botulism",
    "yellow fever": "Yellow Fever",
    "rift valley": "Rift Valley Fever",
    "nipah": "Nipah Virus",
    "hendra": "Hendra Virus",
}


def _categorize(text: str) -> str:
    if not text:
        return "Unknown"
    lower = text.lower()
    for kw, label in DISEASE_CATEGORIES.items():
        if kw in lower:
            return label
    # Return cleaned original
    return text.strip()[:80]


async def fetch_healthmap(lookback_days: int = 90) -> int:
    date_from = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    date_to = date.today().strftime("%Y-%m-%d")

    params = {
        "stripHtml": "1",
        "addlayers": "*",
        "json": "1",
        "limit": "1000",
        "dateFrom": date_from,
        "dateTo": date_to,
    }

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(HEALTHMAP_API, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:
        log.warning("HealthMap fetch failed: %s", e)
        return 0

    # API returns list or wrapped object
    if isinstance(payload, list):
        alerts = payload
    elif isinstance(payload, dict):
        alerts = (
            payload.get("pointsOfInterest")
            or payload.get("alerts")
            or payload.get("data")
            or []
        )
    else:
        log.warning("HealthMap: unexpected response type %s", type(payload))
        return 0

    if not alerts:
        log.info("HealthMap: API returned 0 alerts")
        return 0

    log.info("HealthMap: raw alert count = %d", len(alerts))

    since = date.today() - timedelta(days=lookback_days)
    agg: dict[tuple, dict] = {}

    for alert in alerts:
        try:
            raw_lat = alert.get("lat") or alert.get("latitude") or 0
            raw_lon = (
                alert.get("lon")
                or alert.get("long")
                or alert.get("lng")
                or alert.get("longitude")
                or 0
            )
            lat = round(float(raw_lat), 1)
            lon = round(float(raw_lon), 1)
            if lat == 0.0 and lon == 0.0:
                continue

            raw_date = (
                alert.get("date")
                or alert.get("formatted_date")
                or alert.get("timestamp")
                or alert.get("pub_date")
            )
            if not raw_date:
                continue
            alert_date = date.fromisoformat(str(raw_date)[:10])
            if alert_date < since:
                continue

            week_start = alert_date - timedelta(days=alert_date.weekday())
            disease = _categorize(
                alert.get("disease")
                or alert.get("diseases")
                or alert.get("summary", "")
            )
            country = (
                alert.get("country")
                or alert.get("countryname")
                or alert.get("place_name")
                or ""
            )
            place = (
                alert.get("place_name")
                or alert.get("placename")
                or country
                or f"{lat},{lon}"
            )

            key = (week_start, lat, lon, disease)
            if key not in agg:
                agg[key] = {
                    "lat": lat, "lon": lon,
                    "week_start": week_start,
                    "disease": disease,
                    "place": place[:200],
                    "country": country,
                    "count": 0,
                }
            agg[key]["count"] += 1
        except Exception:
            continue

    if not agg:
        log.info("HealthMap: no aggregatable alerts after filtering")
        return 0

    records = []
    for (week_start, lat, lon, disease), g in agg.items():
        records.append({
            "source": "hmp",
            "site_id": f"hmp_{lat}_{lon}",
            "site_name": g["place"],
            "state": None,
            "county_fips": None,
            "lat": lat,
            "lon": lon,
            "pathogen": disease,
            "signal_date": week_start,
            "metric": "alert_count",
            "value": float(g["count"]),
            "raw": {"country": g["country"]},
        })

    # Deduplicate by constraint key
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

    log.info("HealthMap: upserted %d aggregated event rows", len(records))
    return len(records)
