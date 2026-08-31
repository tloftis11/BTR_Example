"""Orchestrates the full daily pipeline run across all sources."""

import logging
from datetime import datetime

from app.database import AsyncSessionLocal
from app.models import PipelineRun
from app.pipeline.nwss import fetch_nwss
from app.pipeline.tgs import fetch_tgs
from app.pipeline.securebio import fetch_securebio
from app.pipeline.hmp import fetch_healthmap
from app.pipeline.who import fetch_who_don
from app.pipeline.nao import fetch_nao
from app.pipeline.nst import fetch_nextstrain
from app.pipeline.anomaly import run_anomaly_detection
from app.config import settings

log = logging.getLogger(__name__)

SOURCES = [
    ("nwss", fetch_nwss),
    ("tgs", fetch_tgs),
    ("sbd", fetch_securebio),
    ("hmp", fetch_healthmap),
    ("who", fetch_who_don),
    ("nao", fetch_nao),
    ("nst", fetch_nextstrain),
]


async def run_all_sources() -> dict:
    log.info("Pipeline run starting (%d sources)", len(SOURCES))
    summary = {}

    for source, fetch_fn in SOURCES:
        run = PipelineRun(source=source, status="running")
        async with AsyncSessionLocal() as session:
            session.add(run)
            await session.commit()
            await session.refresh(run)

        try:
            rows = await fetch_fn(lookback_days=settings.pull_lookback_days)
            status = "success"
            error = None
        except Exception as e:
            log.exception("Pipeline error for %s", source)
            rows = 0
            status = "error"
            error = str(e)[:2000]

        async with AsyncSessionLocal() as session:
            run_db = await session.get(PipelineRun, run.id)
            run_db.finished_at = datetime.utcnow()
            run_db.rows_inserted = rows
            run_db.status = status
            run_db.error = error
            await session.commit()

        summary[source] = {"status": status, "rows": rows}
        log.info("  %s: %s (%d rows)", source, status, rows)

    try:
        anomaly_count = await run_anomaly_detection()
        summary["anomalies"] = {"status": "success", "count": anomaly_count}
    except Exception as e:
        log.exception("Anomaly detection failed")
        summary["anomalies"] = {"status": "error", "error": str(e)}

    log.info("Pipeline run complete: %s", summary)
    return summary
