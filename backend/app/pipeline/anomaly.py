"""
Anomaly detection: z-score against a rolling baseline window.

For each (site_id, metric) combination, compute the mean and std dev of the
prior N weeks, then flag the current week if (value - mean) / std > threshold.
"""

import logging
from datetime import date

import numpy as np
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Signal, Anomaly

log = logging.getLogger(__name__)


async def run_anomaly_detection() -> int:
    """Recompute anomalies for all sites. Returns number of new anomalies written."""
    window = settings.anomaly_window_weeks
    threshold = settings.anomaly_threshold

    async with AsyncSessionLocal() as session:
        # Pull all signals ordered by site, metric, date
        result = await session.execute(
            select(Signal)
            .where(Signal.value.is_not(None))
            .order_by(Signal.site_id, Signal.metric, Signal.signal_date)
        )
        signals = result.scalars().all()

    if not signals:
        return 0

    # Group by (site_id, metric)
    from itertools import groupby
    from operator import attrgetter

    key = attrgetter("site_id", "metric")
    groups = {k: list(v) for k, v in groupby(sorted(signals, key=lambda s: (s.site_id, s.metric)), key=key)}

    new_anomalies = []

    for (site_id, metric), group in groups.items():
        values = [s.value for s in group]
        dates = [s.signal_date for s in group]

        for i in range(window, len(values)):
            baseline = np.array(values[i - window: i], dtype=float)
            baseline = baseline[~np.isnan(baseline)]
            if len(baseline) < 4:
                continue
            mean = baseline.mean()
            std = baseline.std()
            if std < 1e-9:
                continue
            z = (values[i] - mean) / std
            if abs(z) >= threshold:
                ref = group[i]
                new_anomalies.append({
                    "source": ref.source,
                    "site_id": ref.site_id,
                    "site_name": ref.site_name,
                    "state": ref.state,
                    "lat": ref.lat,
                    "lon": ref.lon,
                    "pathogen": ref.pathogen,
                    "signal_date": ref.signal_date,
                    "metric": metric,
                    "z_score": round(float(z), 3),
                    "current_value": round(float(values[i]), 4),
                    "baseline_mean": round(float(mean), 4),
                    "baseline_std": round(float(std), 4),
                    "is_active": ref.signal_date >= _cutoff(),
                })

    if not new_anomalies:
        return 0

    async with AsyncSessionLocal() as session:
        # Clear existing anomalies and rewrite (full recompute each run)
        await session.execute(delete(Anomaly))
        await session.execute(insert(Anomaly).values(new_anomalies))
        await session.commit()

    log.info("Anomaly detection: wrote %d anomalies", len(new_anomalies))
    return len(new_anomalies)


def _cutoff() -> date:
    from datetime import timedelta
    return date.today() - timedelta(weeks=2)
