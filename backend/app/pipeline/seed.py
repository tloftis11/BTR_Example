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
    """Insert fixture signals if the table has fewer than 10 rows. Returns rows inserted."""
    count = await db.scalar(select(func.count()).select_from(Signal))
    if count and count >= 10:
        log.info("Seed skipped — %d signals already in DB", count)
        return 0

    if not FIXTURE_PATH.exists():
        log.warning("Fixture file not found at %s", FIXTURE_PATH)
        return 0

    with open(FIXTURE_PATH) as f:
        rows = json.load(f)

    inserted = 0
    for r in rows:
        sig = Signal(
            source=r["source"],
            site_id=r["site_id"],
            site_name=r.get("site_name"),
            pathogen=r.get("pathogen"),
            signal_date=r["signal_date"],
            metric=r["metric"],
            value=r.get("value"),
            unit=r.get("unit"),
            region=r.get("region"),
        )
        db.add(sig)
        inserted += 1

    try:
        await db.commit()
        log.info("Seeded %d signals from fixture file", inserted)
    except Exception as e:
        await db.rollback()
        log.warning("Seed commit failed (may be duplicate data): %s", e)

    return inserted
