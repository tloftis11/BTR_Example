from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/biothreat"
    nwss_api_base: str = "https://data.cdc.gov/resource"
    nwss_dataset_id: str = "g653-rqe2"   # NWSS wastewater metric data
    cdc_variants_dataset_id: str = "jr58-6ysp"  # SARS-CoV-2 variant proportions
    socrata_app_token: str = ""
    anthropic_api_key: str = ""
    pull_lookback_days: int = 90
    anomaly_window_weeks: int = 8
    anomaly_threshold: float = 2.0
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
