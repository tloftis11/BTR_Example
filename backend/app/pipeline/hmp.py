"""
Global health event alert pipeline via ReliefWeb Disasters API.

ReliefWeb (United Nations OCHA) maintains a public disasters database tracking
epidemic, outbreak, and public health emergency events globally. This pipeline
pulls recent epidemic-type events and maps them to the signals schema.

API docs: https://reliefweb.int/help/api
Source:   ReliefWeb (powered by UN OCHA)
"""

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

RELIEFWEB_API = "https://api.reliefweb.int/v1/disasters"

# Epidemic / health-related ReliefWeb disaster type IDs
EPIDEMIC_TYPE_IDS = {"4613", "4618"}  # 4613=Epidemic, 4618=other health


async def fetch_healthmap(lookback_days: int = 365) -> int:
    """Pull ReliefWeb epidemic events and upsert as signal records."""
    since_iso = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    payload = {
        "appid": "biothreat-radar",
        "limit": 200,
        "filter": {
            "operator": "AND",
            "conditions": [
                {"field": "type", "value": ["EP", "OT"], "operator": "OR"},
                {"field": "date.created", "value": {"from": since_iso}},
            ],
        },
        "fields": {
            "include": ["id", "name", "date", "country", "status", "type", "glide"],
        },
        "sort": ["date.created:desc"],
    }

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                RELIEFWEB_API,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        log.warning("ReliefWeb fetch failed: %s", e)
        return 0

    items = data.get("data", [])
    log.info("ReliefWeb: %d epidemic events returned", len(items))

    if not items:
        return 0

    records = []
    for item in items:
        try:
            fields = item.get("fields", {})
            name = fields.get("name", "Unknown event")
            created = fields.get("date", {}).get("created", "")
            if not created:
                continue
            event_date = date.fromisoformat(created[:10])

            countries = fields.get("country", [])
            if not countries:
                countries = [{"name": "Global", "location": {"lat": 20.0, "lon": 0.0}}]

            # Extract pathogen/disease category from event name
            disease = _classify_disease(name)
            status = fields.get("status", "ongoing")

            for c in countries:
                country_name = c.get("name", "Unknown")
                loc = c.get("location", {})
                lat = loc.get("lat")
                lon = loc.get("lon")
                if lat is None or lon is None:
                    lat, lon = 20.0, 0.0

                site_id = f"hmp_{country_name[:20].lower().replace(' ', '_')}"
                records.append({
                    "source": "hmp",
                    "site_id": site_id,
                    "site_name": f"RWB: {country_name}",
                    "state": None,
                    "county_fips": None,
                    "lat": lat,
                    "lon": lon,
                    "pathogen": disease,
                    "signal_date": event_date,
                    "metric": "alert_count",
                    "value": 1.0,
                    "raw": {"event_name": name, "status": status, "country": country_name},
                })
        except Exception:
            continue

    if not records:
        return 0

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

    log.info("ReliefWeb: upserted %d epidemic event records", len(records))
    return len(records)


def _classify_disease(name: str) -> str:
    lower = name.lower()
    mapping = {
        "cholera": "Cholera",
        "ebola": "Ebola Virus Disease",
        "mpox": "Mpox",
        "monkeypox": "Mpox",
        "h5n1": "H5N1 Avian Influenza",
        "avian flu": "Avian Influenza",
        "avian influenza": "Avian Influenza",
        "marburg": "Marburg Virus Disease",
        "dengue": "Dengue",
        "lassa": "Lassa Fever",
        "plague": "Plague",
        "yellow fever": "Yellow Fever",
        "meningitis": "Meningitis",
        "covid": "COVID-19",
        "influenza": "Influenza",
        "polio": "Poliomyelitis",
        "measles": "Measles",
        "typhoid": "Typhoid",
        "anthrax": "Anthrax",
        "rift valley": "Rift Valley Fever",
        "nipah": "Nipah Virus",
    }
    for kw, label in mapping.items():
        if kw in lower:
            return label
    return "Epidemic / Unknown"
