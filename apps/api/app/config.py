from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = ""
    backend_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./inferlens.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_mock_mode: bool = True
    openai_api_key: str = ""
    gemini_api_key: str = ""
    default_provider: str = "mock"
    default_model: str = "mock-fast"
    default_context_window: int = Field(default=8, validation_alias="DEFAULT_CONTEXT_WINDOW")
    rate_limit_per_minute: int = 20
    log_level: str = "INFO"
    ingestion_stream: str = "inference_logs"
    dead_letter_stream: str = "dead_letter_logs"
    worker_group: str = "inferlens-workers"
    mock_chunk_delay_ms: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()