from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Anomaly
from app.schemas import AnomalyOut

router = APIRouter()


@router.get("/", response_model=list[AnomalyOut])
async def list_anomalies(
    active_only: bool = True,
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Anomaly).order_by(desc(Anomaly.z_score))
    if active_only:
        q = q.where(Anomaly.is_active == True)
    if source:
        q = q.where(Anomaly.source == source)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
