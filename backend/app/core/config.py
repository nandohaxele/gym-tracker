"""Application settings loaded from environment variables / .env file.

Uses pydantic-settings so the same Settings class works for SQLite (dev)
and PostgreSQL (prod) without code changes - only DATABASE_URL changes.
"""

import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite:///./gym.db"

    jwt_secret: str = "change-me-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Kept as a plain string so pydantic-settings does NOT try to JSON-decode
    # it from the .env file (which would require pydantic-settings >= 2.7 with
    # NoDecode, or quoting the value as a JSON array). The list[str] form is
    # exposed via the `cors_origins` property below.
    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    env: str = "development"

    @property
    def cors_origins(self) -> list[str]:
        """Accept either a JSON list or a comma-separated string from env."""
        value = self.cors_origins_raw.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()
