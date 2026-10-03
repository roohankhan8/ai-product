from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = "postgresql+asyncpg://devuser:devpassword@localhost:5433/devdb"
    redis_url: str = "redis://localhost:6379/0"
    auth_secret: str = "local-development-auth-secret-change-me"
    storage_dir: str = "./storage"
    max_upload_bytes: int = 10 * 1024 * 1024
    llm_provider: Literal["mock", "openai_compatible", "gemini"] = "gemini"
    llm_api_key: str | None = None
    llm_model: str = "gemini-2.0-flash"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    llm_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
