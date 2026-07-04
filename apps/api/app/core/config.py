from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the default SQLite path to an absolute location anchored at
# `apps/api/`, independent of the current working directory uvicorn was
# launched from. This avoids the class of bug where a `./degreepilot.db`
# relative path resolves to whichever directory you happened to `cd` into.
_API_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _API_DIR / "degreepilot.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DP_", env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = f"sqlite:///{_DEFAULT_DB_PATH}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    app_name: str = "DegreePilot API"
    seed_on_startup: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
