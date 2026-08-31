"""
Outbreak news retrieval for briefing context enrichment.

Two-tier approach:
  1. Tavily Search API — if TAVILY_API_KEY is set. Purpose-built for LLM
     applications, runs from datacenter IPs without issue, free up to
     1,000 queries/month (well above the ~31 daily briefings/month needed).
  2. Claude knowledge fallback — if no Tavily key. Returns a structured
     prompt instruction telling the model to draw on its own training
     knowledge of current surveillance concerns and label the source.

Both return a string that is appended to the briefing context block.
"""

import asyncio
import logging
from datetime import date

log = logging.getLogger(__name__)

# Queries run in parallel when Tavily is available
TAVILY_QUERIES = [
    "disease outbreak WHO alert 2026",
    "H5N1 avian influenza human case 2026",
    "mpox monkeypox outbreak 2026",
    "emerging infectious disease surveillance 2026",
    "cholera ebola outbreak latest 2026",
]


async def _tavily_query(client, query: str, max_results: int = 3) -> list[dict]:
    """Run a single Tavily query in a thread pool (SDK is synchronous)."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: client.search(
                query,
                search_depth="basic",
                max_results=max_results,
                include_answer=False,
            ),
        )
        return result.get("results", [])
    except Exception as e:
        log.warning("Tavily query '%s' failed: %s", query, e)
        return []


async def fetch_tavily_news(api_key: str) -> str:
    """
    Run all TAVILY_QUERIES concurrently and format results as a context block.
    Returns empty string on total failure (caller falls back to model knowledge).
    """
    try:
        from tavily import TavilyClient  # imported lazily — optional dependency
        client = TavilyClient(api_key=api_key)
    except ImportError:
        log.warning("tavily-python not installed; falling back to model knowledge")
        return ""

    tasks = [_tavily_query(client, q) for q in TAVILY_QUERIES]
    all_results = await asyncio.gather(*tasks)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    items: list[dict] = []
    for batch in all_results:
        for r in batch:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                items.append(r)

    if not items:
        return ""

    lines = [
        "LIVE OUTBREAK NEWS (via Tavily web search, fetched at briefing time):",
    ]
    for item in items:
        title   = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        url     = (item.get("url") or "").strip()
        if not title:
            continue
        lines.append(f"\n  • {title}")
        if content:
            snippet = content[:350] + ("…" if len(content) > 350 else "")
            lines.append(f"    {snippet}")
        if url:
            lines.append(f"    Source: {url}")

    return "\n".join(lines)


def model_knowledge_context() -> str:
    """
    Returns a prompt instruction telling Claude to supplement sparse pipeline
    data with its own training knowledge, clearly labeled by source.
    Used when no live search API is available.
    """
    today = date.today().isoformat()
    return f"""SUPPLEMENTAL CONTEXT — MODEL TRAINING KNOWLEDGE:
No live news search API is configured. When structured pipeline data is sparse,
draw on your training knowledge of active global biosurveillance concerns as of
your knowledge cutoff. For any claim drawn from training knowledge rather than
the structured data above, prefix it clearly with "[Model knowledge]" so readers
can distinguish live surveillance metrics from background context.

Key ongoing concerns to consider (draw only on what you know is accurate):
- H5N1 avian influenza: US dairy cattle spread, human spillover cases, global poultry situation
- SARS-CoV-2 variant evolution: current dominant lineages, immune escape
- Mpox: Clade Ib situation in DRC and neighboring countries, global Clade IIb baseline
- Cholera: ongoing outbreaks in Yemen, Haiti, sub-Saharan Africa
- WHO IHR surveillance priorities as of your training cutoff
Today's date for the briefing: {today}"""


async def get_news_context(tavily_api_key: str = "") -> str:
    """
    Primary entry point. Returns a context string to append to the briefing.
    Tries Tavily first; falls back to model knowledge instruction.
    """
    if tavily_api_key:
        try:
            result = await fetch_tavily_news(tavily_api_key)
            if result:
                log.info("Tavily news context: %d chars", len(result))
                return result
            log.warning("Tavily returned no results; using model knowledge fallback")
        except Exception as e:
            log.warning("Tavily failed entirely (%s); using model knowledge fallback", e)

    return model_knowledge_context()
