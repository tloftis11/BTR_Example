from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Signal, Anomaly
from app.schemas import SignalOut, TimeSeriesPoint, SiteLatest

router = APIRouter()


@router.get("/sites", response_model=list[SiteLatest])
async def get_sites(
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Latest signal value per site, with anomaly flag."""
    # Subquery: latest signal date per (site_id, metric)
    sub = (
        select(
            Signal.site_id,
            Signal.metric,
            func.max(Signal.signal_date).label("max_date"),
        )
        .group_by(Signal.site_id, Signal.metric)
        .subquery()
    )

    q = (
        select(Signal)
        .join(
            sub,
            and_(
                Signal.site_id == sub.c.site_id,
                Signal.metric == sub.c.metric,
                Signal.signal_date == sub.c.max_date,
            ),
        )
        .where(Signal.metric.in_(["detect_prop_15d", "variant_proportion", "novelty_score"]))
    )
    if source:
        q = q.where(Signal.source == source)

    result = await db.execute(q)
    signals = result.scalars().all()

    # Fetch active anomaly site_ids
    anom_result = await db.execute(
        select(Anomaly.site_id).where(Anomaly.is_active == True).distinct()
    )
    anomaly_sites = {r[0] for r in anom_result}

    return [
        SiteLatest(
            site_id=s.site_id,
            site_name=s.site_name,
            source=s.source,
            state=s.state,
            lat=s.lat,
            lon=s.lon,
            pathogen=s.pathogen,
            latest_date=s.signal_date,
            latest_value=s.value,
            metric=s.metric,
            has_anomaly=s.site_id in anomaly_sites,
        )
        for s in signals
    ]


@router.get("/timeseries", response_model=list[TimeSeriesPoint])
async def get_timeseries(
    source: Literal["nwss", "tgs", "sbd"],
    metric: str = "detect_prop_15d",
    weeks: int = Query(default=13, ge=4, le=52),
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Weekly time series for a given source / metric, optionally filtered by state."""
    since = date.today() - timedelta(weeks=weeks)
    q = (
        select(Signal)
        .where(
            Signal.source == source,
            Signal.metric == metric,
            Signal.signal_date >= since,
            Signal.value.is_not(None),
        )
        .order_by(Signal.signal_date)
    )
    if state:
        q = q.where(Signal.state == state)

    result = await db.execute(q)
    signals = result.scalars().all()

    return [
        TimeSeriesPoint(
            signal_date=s.signal_date,
            value=s.value,
            site_id=s.site_id,
            site_name=s.site_name,
            state=s.state,
        )
        for s in signals
    ]


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Dashboard summary stats."""
    total_sites = await db.scalar(select(func.count(Signal.site_id.distinct())))
    active_anomalies = await db.scalar(
        select(func.count()).where(Anomaly.is_active == True)
    )
    latest_nwss = await db.scalar(
        select(func.max(Signal.signal_date)).where(Signal.source == "nwss")
    )
    latest_tgs = await db.scalar(
        select(func.max(Signal.signal_date)).where(Signal.source == "tgs")
    )

    # Latest national NWSS detect_prop mean
    nwss_latest_date = latest_nwss
    nwss_avg = None
    if nwss_latest_date:
        nwss_avg = await db.scalar(
            select(func.avg(Signal.value)).where(
                Signal.source == "nwss",
                Signal.metric == "detect_prop_15d",
                Signal.signal_date == nwss_latest_date,
                Signal.value.is_not(None),
            )
        )

    return {
        "total_sites": total_sites or 0,
        "active_anomalies": active_anomalies or 0,
        "latest_nwss_date": latest_nwss,
        "latest_tgs_date": latest_tgs,
        "nwss_national_detect_prop": round(float(nwss_avg), 4) if nwss_avg else None,
    }
