from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Signal, Anomaly
from app.schemas import SignalOut, TimeSeriesPoint, SiteLatest

router = APIRouter()

# All primary metrics shown on the sites map
SITE_METRICS = {
    "detect_prop_15d", "variant_proportion", "novelty_score",
    "alert_count", "outbreak_event", "sequencing_runs",
    "h5n1_sequences", "mpox_sequences",
}


@router.get("/sites", response_model=list[SiteLatest])
async def get_sites(
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
):
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
        .where(Signal.metric.in_(SITE_METRICS))
    )
    if source:
        q = q.where(Signal.source == source)

    result = await db.execute(q)
    signals = result.scalars().all()

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
    source: str,
    metric: str = "detect_prop_15d",
    weeks: int = Query(default=13, ge=4, le=104),
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
):
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


@router.get("/variants")
async def get_variants(
    weeks: int = Query(default=13, ge=4, le=52),
    db: AsyncSession = Depends(get_db),
):
    """TGS variant proportions broken out by variant for stacked chart."""
    since = date.today() - timedelta(weeks=weeks)

    result = await db.execute(
        select(
            Signal.signal_date,
            Signal.pathogen,
            func.avg(Signal.value).label("share"),
        )
        .where(
            Signal.source == "tgs",
            Signal.metric == "variant_proportion",
            Signal.signal_date >= since,
            Signal.value.is_not(None),
        )
        .group_by(Signal.signal_date, Signal.pathogen)
        .order_by(Signal.signal_date)
    )
    rows = result.all()

    by_date: dict[str, dict[str, float]] = {}
    variant_totals: dict[str, float] = {}
    for row in rows:
        d = str(row.signal_date)
        v = (row.pathogen or "Unknown").replace("SARS-CoV-2 / ", "")
        share = round(float(row.share), 4)
        if d not in by_date:
            by_date[d] = {}
        by_date[d][v] = share
        variant_totals[v] = variant_totals.get(v, 0) + share

    # Keep top 8 variants by cumulative share
    top_variants = sorted(variant_totals, key=variant_totals.get, reverse=True)[:8]
    dates = sorted(by_date.keys())
    series = [
        {"date": d, **{v: by_date[d].get(v, 0) for v in top_variants}}
        for d in dates
    ]

    return {"variants": top_variants, "series": series}


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
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
    latest_hmp = await db.scalar(
        select(func.max(Signal.signal_date)).where(Signal.source == "hmp")
    )
    latest_who = await db.scalar(
        select(func.max(Signal.signal_date)).where(Signal.source == "who")
    )

    nwss_avg = None
    if latest_nwss:
        nwss_avg = await db.scalar(
            select(func.avg(Signal.value)).where(
                Signal.source == "nwss",
                Signal.metric == "detect_prop_15d",
                Signal.signal_date == latest_nwss,
                Signal.value.is_not(None),
            )
        )

    # Count total active WHO + HMP events in last 30 days
    event_cutoff = date.today() - timedelta(days=30)
    hmp_events = await db.scalar(
        select(func.count()).where(
            Signal.source == "hmp",
            Signal.signal_date >= event_cutoff,
            Signal.value.is_not(None),
        )
    )
    who_events = await db.scalar(
        select(func.count()).where(
            Signal.source == "who",
            Signal.signal_date >= event_cutoff,
        )
    )

    # Actual row counts per source in Signal table
    sources = ["nwss", "tgs", "sbd", "hmp", "who", "nao", "nst"]
    signal_counts = {}
    for src in sources:
        signal_counts[src] = await db.scalar(
            select(func.count()).where(Signal.source == src)
        ) or 0

    return {
        "total_sites": total_sites or 0,
        "active_anomalies": active_anomalies or 0,
        "latest_nwss_date": latest_nwss,
        "latest_tgs_date": latest_tgs,
        "latest_hmp_date": latest_hmp,
        "latest_who_date": latest_who,
        "nwss_national_detect_prop": round(float(nwss_avg), 4) if nwss_avg else None,
        "hmp_events_30d": hmp_events or 0,
        "who_events_30d": who_events or 0,
        "signal_counts": signal_counts,
    }
