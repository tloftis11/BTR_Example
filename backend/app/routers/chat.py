"""LLM-powered data analysis endpoints backed by Anthropic."""

import logging
from datetime import date, timedelta

import anthropic
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Anomaly, PipelineRun, Signal

log = logging.getLogger(__name__)
router = APIRouter()

SYSTEM_PROMPT = """You are an epidemiological analyst for Biothreat Radar, a 7-stream global biosurveillance platform.

Your role is to synthesize data from these surveillance streams:
- NWSS: National Wastewater Surveillance System — SARS-CoV-2 detection proportion across US treatment plants
- TGS: Traveler Genomic Surveillance — SARS-CoV-2 variant proportions from US airport travelers
- SBD: SecureBio Environmental Detection — metagenomic novelty scores
- HMP: HealthMap — automated global disease event detection from news, ProMED, WHO feeds
- WHO: WHO Disease Outbreak News — formally declared international outbreak events
- NAO: Nucleic Acid Observatory — NCBI SRA metagenomic sequencing runs (PRJNA729801)
- NST: Nextstrain — H5N1 avian influenza and Mpox sequence counts by country

When writing briefings or answering questions:
- Be precise and factual, citing specific metrics when available
- Flag when data is absent or sparse
- Note cross-stream concordance (e.g., rising wastewater + rising variant diversity = higher concern)
- Use epidemiological language appropriate for public health professionals
- Keep briefings to 3-4 concise paragraphs
- Explicitly state what you cannot determine from the available data
- Do NOT speculate beyond what the data supports"""


async def _build_context(db: AsyncSession) -> str:
    """Query DB for current surveillance state and format as context string."""
    since = date.today() - timedelta(days=90)

    # Active anomalies
    anom_res = await db.execute(
        select(Anomaly)
        .where(Anomaly.is_active == True)
        .order_by(desc(Anomaly.z_score))
        .limit(10)
    )
    anomalies = anom_res.scalars().all()

    # NWSS latest national average
    nwss_date = await db.scalar(
        select(func.max(Signal.signal_date)).where(Signal.source == "nwss")
    )
    nwss_avg = None
    if nwss_date:
        nwss_avg = await db.scalar(
            select(func.avg(Signal.value)).where(
                Signal.source == "nwss",
                Signal.metric == "detect_prop_15d",
                Signal.signal_date == nwss_date,
                Signal.value.is_not(None),
            )
        )

    # TGS top variants (last 30 days)
    tgs_since = date.today() - timedelta(days=30)
    tgs_res = await db.execute(
        select(Signal.pathogen, func.avg(Signal.value).label("avg_share"))
        .where(
            Signal.source == "tgs",
            Signal.metric == "variant_proportion",
            Signal.signal_date >= tgs_since,
            Signal.value.is_not(None),
        )
        .group_by(Signal.pathogen)
        .order_by(desc("avg_share"))
        .limit(8)
    )
    top_variants = tgs_res.all()

    # Latest pipeline run status
    run_res = await db.execute(
        select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(6)
    )
    runs = run_res.scalars().all()

    # Format context
    lines = [f"SURVEILLANCE DATA AS OF {date.today().isoformat()}",
             "=" * 50, ""]

    lines.append("NWSS WASTEWATER SURVEILLANCE:")
    if nwss_date and nwss_avg is not None:
        lines.append(f"  Latest date: {nwss_date}")
        lines.append(f"  National detection proportion (detect_prop_15d): {nwss_avg:.4f} ({nwss_avg*100:.2f}%)")
    else:
        lines.append("  No NWSS data available.")

    lines.append("")
    lines.append("TGS VARIANT PROPORTIONS (30-day avg):")
    if top_variants:
        for r in top_variants:
            name = (r.pathogen or "Unknown").replace("SARS-CoV-2 / ", "")
            lines.append(f"  {name}: {r.avg_share:.4f} ({r.avg_share*100:.1f}%)")
    else:
        lines.append("  No TGS variant data available.")

    lines.append("")
    lines.append("ACTIVE ANOMALIES (z-score ≥ 2.0, past 14 days):")
    if anomalies:
        for a in anomalies:
            lines.append(
                f"  [{a.source.upper()}] {a.site_name or a.site_id} | {a.pathogen} | "
                f"z={a.z_score:.2f} | value={a.current_value:.4f} | date={a.signal_date}"
            )
    else:
        lines.append("  No active anomalies detected.")

    # HMP + WHO event counts
    event_cutoff = date.today() - timedelta(days=30)
    hmp_count = await db.scalar(
        select(func.count()).where(Signal.source == "hmp", Signal.signal_date >= event_cutoff)
    ) or 0
    who_count = await db.scalar(
        select(func.count()).where(Signal.source == "who", Signal.signal_date >= event_cutoff)
    ) or 0

    # Nextstrain latest
    nst_h5n1 = await db.scalar(
        select(func.sum(Signal.value)).where(
            Signal.source == "nst", Signal.metric == "h5n1_sequences",
            Signal.signal_date >= date.today() - timedelta(days=30),
        )
    )
    nst_mpox = await db.scalar(
        select(func.sum(Signal.value)).where(
            Signal.source == "nst", Signal.metric == "mpox_sequences",
            Signal.signal_date >= date.today() - timedelta(days=30),
        )
    )

    lines.append("")
    lines.append("GLOBAL ALERT STREAMS (30 days):")
    lines.append(f"  HealthMap alert clusters: {hmp_count}")
    lines.append(f"  WHO DON outbreak events: {who_count}")
    lines.append(f"  Nextstrain H5N1 sequences: {int(nst_h5n1) if nst_h5n1 else 'no data'}")
    lines.append(f"  Nextstrain Mpox sequences: {int(nst_mpox) if nst_mpox else 'no data'}")

    lines.append("")
    lines.append("PIPELINE STATUS (last runs):")
    by_source: dict[str, str] = {}
    for r in runs:
        if r.source not in by_source:
            by_source[r.source] = (
                f"  {r.source.upper()}: {r.status} | "
                f"rows={r.rows_inserted} | {r.started_at.date()}"
            )
    for line in by_source.values():
        lines.append(line)

    return "\n".join(lines)


class ChatRequest(BaseModel):
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


@router.post("/briefing")
async def get_briefing(db: AsyncSession = Depends(get_db)):
    """Generate a situation briefing from current surveillance data."""
    if not settings.anthropic_api_key:
        return {"error": "ANTHROPIC_API_KEY not configured on server."}

    context = await _build_context(db)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    "Generate a concise situation briefing for public health analysts. "
                    "Summarize the current surveillance picture, highlight any notable signals "
                    "or cross-stream concordance, and note data gaps.\n\n"
                    + context
                ),
            }],
        )
        return {"briefing": response.content[0].text, "data_context": context}
    except Exception as e:
        log.exception("Anthropic briefing failed")
        return {"error": str(e)}


@router.post("/message")
async def chat_message(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat with the surveillance data using natural language."""
    if not settings.anthropic_api_key:
        return {"error": "ANTHROPIC_API_KEY not configured on server."}

    context = await _build_context(db)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Prepend data context as a system-level user message
    context_msg = {
        "role": "user",
        "content": f"Current surveillance data context:\n\n{context}\n\n---\nYou may now answer questions about this data.",
    }
    ack_msg = {"role": "assistant", "content": "Understood. I have reviewed the current surveillance data. What would you like to know?"}

    messages = [context_msg, ack_msg] + body.messages

    try:
        response = await client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return {"reply": response.content[0].text}
    except Exception as e:
        log.exception("Anthropic chat failed")
        return {"error": str(e)}
