from datetime import date, datetime
from pydantic import BaseModel


class SignalOut(BaseModel):
    id: int
    source: str
    site_id: str
    site_name: str | None
    state: str | None
    lat: float | None
    lon: float | None
    pathogen: str | None
    signal_date: date
    metric: str
    value: float | None

    class Config:
        from_attributes = True


class AnomalyOut(BaseModel):
    id: int
    source: str
    site_id: str
    site_name: str | None
    state: str | None
    lat: float | None
    lon: float | None
    pathogen: str | None
    signal_date: date
    metric: str
    z_score: float
    current_value: float
    baseline_mean: float
    baseline_std: float
    is_active: bool
    detected_at: datetime

    class Config:
        from_attributes = True


class TimeSeriesPoint(BaseModel):
    signal_date: date
    value: float | None
    site_id: str
    site_name: str | None
    state: str | None


class SiteLatest(BaseModel):
    site_id: str
    site_name: str | None
    source: str
    state: str | None
    lat: float | None
    lon: float | None
    pathogen: str | None
    latest_date: date | None
    latest_value: float | None
    metric: str
    has_anomaly: bool


class PipelineRunOut(BaseModel):
    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None
    rows_inserted: int
    status: str
    error: str | None

    class Config:
        from_attributes = True
