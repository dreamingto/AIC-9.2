from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    app_env: str = "development"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://tuji:tuji@localhost:5432/tuji"
    sync_database_url: str = "postgresql+psycopg://tuji:tuji@localhost:5432/tuji"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    data_root: Path = Path("backend/data")
    manifest_root: Path = Path("backend/data/manifests")
    asset_root: Path = Path("backend/data/assets")
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 25_000_000
    top_k_default: int = 10
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
