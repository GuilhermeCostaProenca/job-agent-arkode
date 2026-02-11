from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "job-agent-arkode"
    environment: str = "dev"
    database_url: str = "sqlite:///jobagent.db"
    artifacts_dir: Path = Path("artifacts")
    profile_path: Path = Path("data/profile.yaml")
    profile_dynamic_path: Path = Path("data/profile_dynamic.json")
    daily_cron: str = "0 8 * * *"
    autopilot_enabled: bool = False
    max_jobs_per_run: int = 30
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_sender: str | None = None
    run_id_prefix: str = Field(default="run")
    user_id: str = "default"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings
