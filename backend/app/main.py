from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from fastapi import Depends
from app.database import init_db, AsyncSessionLocal, get_db
from app.routers import signals, anomalies, pipeline as pipeline_router, chat as chat_router, briefing as briefing_router
from app.pipeline.runner import run_all_sources
from app.pipeline.seed import seed_if_empty
from sqlalchemy.ext.asyncio import AsyncSession

scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_if_empty(db)
    scheduler.add_job(run_all_sources, "cron", hour=6, minute=0, id="daily_pull")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Biothreat Radar API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(anomalies.router, prefix="/api/anomalies", tags=["anomalies"])
app.include_router(pipeline_router.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["chat"])
app.include_router(briefing_router.router, prefix="/api/briefing", tags=["briefing"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/admin/reseed")
async def admin_reseed(db: AsyncSession = Depends(get_db)):
    """Force-seed missing sources from fixture file. Safe to call repeatedly."""
    inserted = await seed_if_empty(db)
    return {"inserted": inserted, "message": f"Seeded {inserted} rows for sources with no existing data."}
