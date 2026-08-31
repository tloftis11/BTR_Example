from datetime import date, datetime
from sqlalchemy import String, Float, Date, DateTime, Boolean, Integer, JSON, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("source", "site_id", "pathogen", "signal_date", "metric", name="uq_signal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20))          # nwss | tgs | sbd
    site_id: Mapped[str] = mapped_column(String(100))
    site_name: Mapped[str | None] = mapped_column(String(300))
    state: Mapped[str | None] = mapped_column(String(2))
    county_fips: Mapped[str | None] = mapped_column(String(5))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    pathogen: Mapped[str | None] = mapped_column(String(100))
    signal_date: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(50))           # detect_prop | ptc | variant_prop | novelty
    value: Mapped[float | None] = mapped_column(Float)
    raw: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    site_id: Mapped[str] = mapped_column(String(100))
    site_name: Mapped[str | None] = mapped_column(String(300))
    state: Mapped[str | None] = mapped_column(String(2))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    pathogen: Mapped[str | None] = mapped_column(String(100))
    signal_date: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(50))
    z_score: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float)
    baseline_mean: Mapped[float] = mapped_column(Float)
    baseline_std: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | success | error
    error: Mapped[str | None] = mapped_column(String(2000))


class DailyBriefing(Base):
    """AI-generated daily surveillance briefing, stored after each cron run."""
    __tablename__ = "daily_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    briefing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    content: Mapped[str] = mapped_column(Text, nullable=False)
    data_context: Mapped[str | None] = mapped_column(Text)       # raw context fed to LLM
    filters_json: Mapped[dict | None] = mapped_column(JSON)      # filter params if custom
    model_id: Mapped[str | None] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)  # False = user-generated custom
