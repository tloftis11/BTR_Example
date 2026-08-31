"""
WHO Disease Outbreak News (DON) pipeline.

Fetches WHO's public RSS feed for internationally notifiable disease events.
Tries multiple candidate URLs since WHO periodically restructures their site.
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models import Signal

log = logging.getLogger(__name__)

# Try multiple known/candidate WHO DON RSS URLs in order
WHO_DON_URLS = [
    "https://www.who.int/csr/don/en/rss.xml",
    "https://www.who.int/feeds/entity/csr/don/en/rss.xml",
    "https://www.who.int/rss-feeds/news-releases.xml",
    "https://www.who.int/feeds/entity/news/en/rss.xml",
]

# Approximate country centroids for WHO event location parsing
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "Afghanistan": (33.9, 67.7), "Angola": (-11.2, 17.9), "Argentina": (-38.4, -63.6),
    "Azerbaijan": (40.1, 47.6), "Bangladesh": (23.7, 90.4), "Bolivia": (-16.3, -63.6),
    "Brazil": (-14.2, -51.9), "Burundi": (-3.4, 29.9), "Cambodia": (12.6, 104.9),
    "Cameroon": (3.9, 11.5), "Central African Republic": (6.6, 20.9), "Chad": (15.5, 18.7),
    "China": (35.9, 104.2), "Colombia": (4.6, -74.1),
    "Democratic Republic of the Congo": (-4.0, 21.8), "DRC": (-4.0, 21.8),
    "Egypt": (26.8, 30.8), "Ethiopia": (9.1, 40.5), "Ghana": (7.9, -1.0),
    "Guinea": (11.0, -10.9), "Haiti": (18.9, -72.3), "India": (20.6, 78.9),
    "Indonesia": (-0.8, 113.9), "Iran": (32.4, 53.7), "Iraq": (33.2, 43.7),
    "Japan": (36.2, 138.3), "Jordan": (30.6, 36.2), "Kenya": (-0.0, 37.9),
    "Laos": (19.9, 102.5), "Lao People's Democratic Republic": (19.9, 102.5),
    "Lebanon": (33.9, 35.9), "Liberia": (6.4, -9.4), "Libya": (26.3, 17.2),
    "Madagascar": (-18.8, 46.9), "Malawi": (-13.3, 34.3), "Malaysia": (4.2, 101.9),
    "Mali": (17.6, -4.0), "Mexico": (23.6, -102.6), "Morocco": (31.8, -7.1),
    "Mozambique": (-18.7, 35.5), "Myanmar": (21.9, 95.9), "Nepal": (28.4, 84.1),
    "Niger": (17.6, 8.1), "Nigeria": (9.1, 8.7), "Pakistan": (30.4, 69.3),
    "Papua New Guinea": (-6.3, 143.9), "Peru": (-9.2, -75.0),
    "Philippines": (12.9, 121.8), "Republic of Korea": (35.9, 127.8),
    "Russia": (61.5, 105.3), "Rwanda": (-1.9, 29.9), "Saudi Arabia": (23.9, 45.1),
    "Senegal": (14.5, -14.5), "Sierra Leone": (8.5, -11.8), "Somalia": (5.2, 46.2),
    "South Africa": (-30.6, 22.9), "South Sudan": (6.9, 31.3), "Sudan": (12.9, 30.2),
    "Syria": (34.8, 38.9), "Syrian Arab Republic": (34.8, 38.9),
    "Tanzania": (-6.4, 34.9), "Thailand": (15.9, 100.9), "Timor-Leste": (-8.9, 125.7),
    "Turkey": (38.9, 35.2), "Turkiye": (38.9, 35.2), "Uganda": (1.4, 32.3),
    "Ukraine": (48.4, 31.2), "United States": (37.1, -95.7), "USA": (37.1, -95.7),
    "United States of America": (37.1, -95.7), "Vietnam": (14.1, 108.3),
    "Viet Nam": (14.1, 108.3), "Yemen": (15.6, 48.5), "Zambia": (-13.1, 27.8),
    "Zimbabwe": (-19.0, 29.2), "Worldwide": (20.0, 0.0), "World": (20.0, 0.0),
    "Global": (20.0, 0.0), "Multiple countries": (20.0, 0.0),
    "Europe": (54.5, 25.3), "Africa": (1.7, 17.5), "Americas": (8.8, -79.5),
    "Western Pacific": (10.4, 142.7), "Eastern Mediterranean": (24.7, 46.7),
    "South-East Asia": (8.5, 95.9),
}


async def _try_fetch_rss(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "BiothreatRadar/1.0"},
            )
            if resp.status_code == 200:
                log.info("WHO DON: got 200 from %s", url)
                return resp.text
            log.debug("WHO DON: %s returned %s", url, resp.status_code)
    except Exception as e:
        log.debug("WHO DON: %s failed: %s", url, e)
    return None


def _parse_location(title: str) -> tuple[str, str, float, float]:
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2:
        disease_raw = parts[0].strip()
        location_raw = re.split(r"\s*[–—]\s*update\b", parts[1], flags=re.IGNORECASE)[0].strip()
        coords = COUNTRY_COORDS.get(location_raw)
        if not coords:
            for key, c in COUNTRY_COORDS.items():
                if key.lower() in location_raw.lower() or location_raw.lower() in key.lower():
                    coords = c
                    break
        if coords:
            return disease_raw[:100], location_raw, coords[0], coords[1]
        return disease_raw[:100], location_raw, 20.0, 0.0
    return title[:100], "Unknown", 20.0, 0.0


async def fetch_who_don(lookback_days: int = 180) -> int:
    """Pull WHO Disease Outbreak News and upsert. Returns rows inserted."""
    since = date.today() - timedelta(days=lookback_days)

    # Try candidate URLs
    xml_text = None
    for url in WHO_DON_URLS:
        xml_text = await _try_fetch_rss(url)
        if xml_text:
            break

    if not xml_text:
        log.warning("WHO DON: all RSS URL candidates returned no data")
        return 0

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning("WHO DON: XML parse error: %s", e)
        return 0

    items = root.findall(".//item")
    log.info("WHO DON: %d items in feed", len(items))

    records = []
    for item in items:
        try:
            title = (item.findtext("title") or "").strip()
            pub_str = item.findtext("pubDate") or ""
            link = item.findtext("link") or ""

            if not title or not pub_str:
                continue

            event_date = parsedate_to_datetime(pub_str).date()
            if event_date < since:
                continue

            disease, country, lat, lon = _parse_location(title)
            site_id = f"who_{country.lower()[:30].replace(' ', '_').replace('(', '').replace(')', '')}"

            records.append({
                "source": "who",
                "site_id": site_id,
                "site_name": f"WHO: {country}",
                "state": None,
                "county_fips": None,
                "lat": lat,
                "lon": lon,
                "pathogen": disease,
                "signal_date": event_date,
                "metric": "outbreak_event",
                "value": 1.0,
                "raw": {"title": title, "link": link, "country": country},
            })
        except Exception:
            continue

    if not records:
        log.info("WHO DON: no parseable recent events")
        return 0

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

    log.info("WHO DON: upserted %d outbreak records", len(records))
    return len(records)
