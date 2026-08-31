from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PipelineRun
from app.pipeline.runner import run_all_sources
from app.schemas import PipelineRunOut

router = APIRouter()


@router.post("/run")
async def trigger_run(background_tasks: BackgroundTasks):
    """Manually trigger a full pipeline run (runs in background)."""
    background_tasks.add_task(run_all_sources)
    return {"status": "started"}


@router.get("/runs", response_model=list[PipelineRunOut])
async def get_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit)
    )
    return result.scalars().all()
