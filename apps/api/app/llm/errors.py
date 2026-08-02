import re
from dataclasses import dataclass, field
from typing import Any


ERROR_HTTP_STATUS = {
    "authentication_error": 401,
    "invalid_request": 400,
    "unsupported_model": 400,
    "provider_rate_limit": 429,
    "timeout": 504,
    "connection_error": 502,
    "provider_unavailable": 503,
    "provider_server_error": 502,
    "content_policy_error": 400,
    "token_limit_error": 400,
    "client_cancelled": 499,
    "stream_interrupted": 502,
    "redis_error": 503,
    "database_error": 503,
    "worker_error": 500,
    "unknown_error": 500,
}
RETRYABLE = {"provider_rate_limit", "timeout", "connection_error", "provider_unavailable", "provider_server_error", "stream_interrupted", "redis_error", "database_error", "worker_error"}


@dataclass
class NormalizedError(Exception):
    category: str = "unknown_error"
    safe_message: str = "The request could not be completed."
    retryable: bool = False
    http_status: int = 500
    provider: str | None = None
    provider_status_code: int | None = None
    trace_id: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.safe_message

    @property
    def error_type(self) -> str:  # legacy persistence/API compatibility
        return self.category


class LLMError(NormalizedError):
    category = "unknown_error"
    error_type = "unknown_error"
    retryable = False

    def __init__(self, message: str, *, retryable: bool | None = None, provider: str | None = None, status_code: int | None = None):
        category = self.error_type
        super().__init__(category, sanitize_error_message(message), self.retryable if retryable is None else retryable, ERROR_HTTP_STATUS.get(category, 500), provider, status_code)


class ProviderTimeoutError(LLMError):
    error_type = "timeout"
    retryable = True


class ProviderRateLimitError(LLMError):
    error_type = "provider_rate_limit"
    retryable = True


class ProviderAuthError(LLMError):
    error_type = "authentication_error"


class ProviderServerError(LLMError):
    error_type = "provider_server_error"
    retryable = True


class ProviderUnavailableError(LLMError):
    error_type = "provider_unavailable"
    retryable = True


class ConnectionError(LLMError):
    error_type = "connection_error"
    retryable = True


class InvalidRequestError(LLMError):
    error_type = "invalid_request"


class StreamInterruptedError(LLMError):
    error_type = "stream_interrupted"
    retryable = True


class UserCancelledError(LLMError):
    error_type = "client_cancelled"


class ProviderModelInvalidError(LLMError):
    error_type = "unsupported_model"


class ProviderModelNotFoundError(ProviderModelInvalidError):
    pass


class ProviderNotFoundError(ProviderModelInvalidError):
    pass


class CircuitOpenError(LLMError):
    error_type = "provider_unavailable"
    retryable = True


def sanitize_error_message(message: str) -> str:
    cleaned = message or ""
    cleaned = re.sub(r"https?://\S+", "[redacted-url]", cleaned)
    cleaned = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer [REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"([?&](?:key|api_key|token)=)[^&\s]+", r"\1[REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:AIza|sk-)[0-9A-Za-z\-_.]+", "[REDACTED]", cleaned)
    cleaned = re.sub(r"(?:postgres(?:ql)?|redis)://[^\s]+", "[redacted-connection-string]", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()[:500]


def normalize_exception(exc: Exception, provider: str | None = None, trace_id: str | None = None) -> NormalizedError:
    if isinstance(exc, NormalizedError):
        exc.provider = exc.provider or provider
        exc.trace_id = exc.trace_id or trace_id
        return exc
    return NormalizedError(
        category="unknown_error",
        safe_message=sanitize_error_message(str(exc)) or "The request could not be completed.",
        retryable=False,
        http_status=500,
        provider=provider,
        trace_id=trace_id,
    )
