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
    # Explicit true forces deterministic Mock traffic. False still selects Mock when no real key exists.
    llm_mock_mode: bool = False
    openai_api_key: str = ""
    gemini_api_key: str = ""
    # Gemini 2.5 Flash charges its thinking tokens against maxOutputTokens. Keep
    # chat answers readable by default; set -1 to restore dynamic thinking.
    gemini_thinking_budget: int = 0
    default_provider: str = "mock"
    default_model: str = "mock-fast"
    default_context_window: int = Field(default=8, validation_alias="DEFAULT_CONTEXT_WINDOW")
    rate_limit_per_minute: int = 20
    log_level: str = "INFO"
    ingestion_stream: str = "inference_logs"
    dead_letter_stream: str = "dead_letter_logs"
    worker_group: str = "inferlens-workers"
    mock_chunk_delay_ms: int = 15
    provider_timeout_seconds: float = 30.0
    provider_max_retries: int = 1
    provider_retry_base_ms: int = 150
    provider_fallbacks: str = "{}"
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_seconds: int = 30
    content_capture_enabled: bool = False
    content_capture_preview_limit: int = 500
    comparison_max_concurrency: int = 3
    worker_retry_limit: int = 3
    worker_stale_claim_ms: int = 60000
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""
    external_trace_url_template: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
