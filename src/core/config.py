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
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    gmail_refresh_token: str | None = None
    github_token: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    llm_enabled: bool = False
    browser_storage_dir: Path = Path("artifacts/browser")
    run_id_prefix: str = Field(default="run")
    user_id: str = "default"
    live_browser_enabled: bool = False
    playwright_headless: bool = True
    linkedin_session_setup_timeout_seconds: int = 300
    daily_application_limit: int = 30
    platform_application_limit: int = 10
    max_retries_per_connector: int = 2
    retry_backoff_window_minutes: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    settings.browser_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
