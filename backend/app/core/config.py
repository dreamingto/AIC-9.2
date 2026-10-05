from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EAFRConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    beta_v: float = Field(default=0.25, ge=0, le=1)
    beta_t: float = Field(default=0.25, ge=0, le=1)
    beta_r: float = Field(default=0.20, ge=0, le=1)
    beta_f: float = Field(default=0.20, ge=0, le=1)
    beta_g: float = Field(default=0.05, ge=0, le=1)
    lambda_e: float = Field(default=0.10, ge=0, le=1)
    lambda_u: float = Field(default=0.05, ge=0, le=1)


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
    retrieval_profile: Literal["baseline", "neural"] = "baseline"
    model_service_url: str = "http://127.0.0.1:8767"
    model_timeout_seconds: float = Field(default=60.0, ge=1.0, le=300.0)
    eafr_weights: EAFRConfig = Field(default_factory=EAFRConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
