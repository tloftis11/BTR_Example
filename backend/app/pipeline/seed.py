"""
Database seeder — loads signals_seed.json into the DB if the signals
table is empty. Runs automatically on startup so Render always has data.
"""

import json
import logging
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Signal

log = logging.getLogger(__name__)

FIXTURE_PATH = Path(__file__).parent.parent.parent / "seed" / "signals_seed.json"


async def seed_if_empty(db: AsyncSession) -> int:
    """
    Seed missing sources from fixture file.
    Checks each source independently — sources that already have data are skipped,
    so existing pipeline data is never overwritten.
    Returns total rows inserted.
    """
    if not FIXTURE_PATH.exists():
        log.warning("Fixture file not found at %s", FIXTURE_PATH)
        return 0

    with open(FIXTURE_PATH) as f:
        all_rows = json.load(f)

    # Group fixture rows by source
    by_source: dict[str, list[dict]] = {}
    for r in all_rows:
        by_source.setdefault(r["source"], []).append(r)

    total_inserted = 0
    for source, rows in by_source.items():
        existing = await db.scalar(
            select(func.count()).select_from(Signal).where(Signal.source == source)
        )
        if existing and existing > 0:
            log.info("Seed skipped for %s — %d rows already in DB", source, existing)
            continue

        inserted = 0
        for r in rows:
            db.add(Signal(
                source=r["source"],
                site_id=r["site_id"],
                site_name=r.get("site_name"),
                pathogen=r.get("pathogen"),
                signal_date=r["signal_date"],
                metric=r["metric"],
                value=r.get("value"),
                unit=r.get("unit"),
                region=r.get("region"),
            ))
            inserted += 1

        try:
            await db.commit()
            log.info("Seeded %d %s rows from fixture", inserted, source)
            total_inserted += inserted
        except Exception as e:
            await db.rollback()
            log.warning("Seed commit failed for %s: %s", source, e)

    return total_inserted
