"""
Reliable RSS/Atom feed fetcher for biosurveillance news.

These feeds are far more stable than structured government APIs — they are
plain HTTP GET + XML with no auth, no pagination, and no schema drift.
Results are used to enrich the briefing context at generation time.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

log = logging.getLogger(__name__)

FEEDS = [
    {
        "id": "promed",
        "name": "ProMED",
        "url": "https://promedmail.org/feed/",
        "desc": "Disease outbreak reports (ProMED international alerting system)",
    },
    {
        "id": "who_news",
        "name": "WHO News",
        "url": "https://www.who.int/rss-feeds/news-releases-en.xml",
        "desc": "WHO official news releases (includes outbreak declarations)",
    },
    {
        "id": "cdc_han",
        "name": "CDC HAN",
        "url": "https://emergency.cdc.gov/han/han.atom",
        "desc": "CDC Health Alert Network advisories",
    },
    {
        "id": "ecdc",
        "name": "ECDC",
        "url": "https://www.ecdc.europa.eu/en/rss-feeds/all-ecdc-publications-items",
        "desc": "European CDC threat assessments and rapid risk assessments",
    },
    {
        "id": "reliefweb",
        "name": "ReliefWeb Epidemics",
        "url": "https://reliefweb.int/updates/rss.xml?primary_country=0&report_type=AL&theme=4590",
        "desc": "ReliefWeb alerts tagged with epidemic/disease outbreak theme",
    },
]

# Namespace maps for Atom feeds
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}


@dataclass
class FeedItem:
    feed_id: str
    feed_name: str
    title: str
    link: str
    published: str   # ISO date string
    summary: str     # truncated to 400 chars


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_rss(feed_id: str, feed_name: str, xml_text: str, max_items: int = 5) -> list[FeedItem]:
    """Parse RSS 2.0 feed."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning("RSS parse error for %s: %s", feed_id, e)
        return []

    items = []
    for item in root.iter("item"):
        if len(items) >= max_items:
            break
        title   = _strip_html((item.findtext("title") or "").strip())
        link    = (item.findtext("link") or "").strip()
        pub     = (item.findtext("pubDate") or item.findtext("dc:date", namespaces=_NS) or "").strip()
        desc    = _strip_html(item.findtext("description") or "")
        summary = desc[:400] + ("…" if len(desc) > 400 else "")
        if title:
            items.append(FeedItem(feed_id, feed_name, title, link, pub, summary))
    return items


def _parse_atom(feed_id: str, feed_name: str, xml_text: str, max_items: int = 5) -> list[FeedItem]:
    """Parse Atom 1.0 feed."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning("Atom parse error for %s: %s", feed_id, e)
        return []

    ns = "http://www.w3.org/2005/Atom"
    items = []
    for entry in root.iter(f"{{{ns}}}entry"):
        if len(items) >= max_items:
            break
        title_el = entry.find(f"{{{ns}}}title")
        title    = _strip_html((title_el.text or "") if title_el is not None else "")
        link_el  = entry.find(f"{{{ns}}}link")
        link     = link_el.get("href", "") if link_el is not None else ""
        pub_el   = entry.find(f"{{{ns}}}published") or entry.find(f"{{{ns}}}updated")
        pub      = (pub_el.text or "") if pub_el is not None else ""
        sum_el   = entry.find(f"{{{ns}}}summary") or entry.find(f"{{{ns}}}content")
        raw_sum  = (sum_el.text or "") if sum_el is not None else ""
        desc     = _strip_html(raw_sum)
        summary  = desc[:400] + ("…" if len(desc) > 400 else "")
        if title:
            items.append(FeedItem(feed_id, feed_name, title, link, pub, summary))
    return items


def _parse_feed(feed_id: str, feed_name: str, xml_text: str) -> list[FeedItem]:
    """Auto-detect RSS vs Atom and parse."""
    if "<feed" in xml_text[:500] or 'xmlns="http://www.w3.org/2005/Atom"' in xml_text[:500]:
        return _parse_atom(feed_id, feed_name, xml_text)
    return _parse_rss(feed_id, feed_name, xml_text)


async def _fetch_one(client: httpx.AsyncClient, feed: dict) -> list[FeedItem]:
    try:
        r = await client.get(
            feed["url"],
            timeout=12,
            headers={"User-Agent": "BiothreatRadar/1.0 (biosurveillance research)"},
            follow_redirects=True,
        )
        if r.status_code != 200:
            log.warning("RSS feed %s returned HTTP %d", feed["id"], r.status_code)
            return []
        return _parse_feed(feed["id"], feed["name"], r.text)
    except Exception as e:
        log.warning("RSS fetch failed for %s: %s", feed["id"], e)
        return []


async def fetch_all_rss(max_items_per_feed: int = 5) -> list[FeedItem]:
    """
    Concurrently fetch all RSS feeds and return a flat list of recent items.
    Failures are silent — the briefing context just has fewer items.
    """
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_fetch_one(client, feed) for feed in FEEDS],
            return_exceptions=True,
        )

    items: list[FeedItem] = []
    for r in results:
        if isinstance(r, list):
            items.extend(r[:max_items_per_feed])
    return items


def format_rss_context(items: list[FeedItem]) -> str:
    """Format RSS items as a context block for the briefing prompt."""
    if not items:
        return "LIVE OUTBREAK NEWS FEEDS:\n  No RSS items retrieved at this time.\n"

    lines = ["LIVE OUTBREAK NEWS FEEDS (fetched at briefing generation time):"]
    current_feed = None
    for item in items:
        if item.feed_name != current_feed:
            current_feed = item.feed_name
            lines.append(f"\n  [{item.feed_name}]")
        lines.append(f"  • {item.title}")
        if item.published:
            lines.append(f"    Published: {item.published}")
        if item.summary:
            lines.append(f"    {item.summary}")
    return "\n".join(lines)
