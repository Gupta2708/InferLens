"""Best-effort, low-cardinality Prometheus metrics."""
from contextlib import suppress

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    REQUESTS = Counter("inferlens_requests_total", "LLM requests", ["provider", "model", "status", "operation"])
    ERRORS = Counter("inferlens_request_errors_total", "LLM request errors", ["provider", "model", "error_type"])
    CANCELLATIONS = Counter("inferlens_request_cancellations_total", "Cancelled requests", ["provider", "model"])
    DURATION = Histogram("inferlens_request_duration_seconds", "LLM latency", ["provider", "model", "status"])
    TTFT = Histogram("inferlens_time_to_first_token_seconds", "Time to first token", ["provider", "model"])
    INPUT_TOKENS = Counter("inferlens_input_tokens_total", "Input tokens", ["provider", "model"])
    OUTPUT_TOKENS = Counter("inferlens_output_tokens_total", "Output tokens", ["provider", "model"])
    COST = Counter("inferlens_estimated_cost_total", "Estimated cost", ["provider", "model"])
    RETRIES = Counter("inferlens_provider_retries_total", "Provider retries", ["provider", "model", "error_type"])
    FALLBACKS = Counter("inferlens_provider_fallbacks_total", "Provider fallbacks", ["provider", "model"])
    REDIS = Counter("inferlens_redis_publish_total", "Redis publishes", ["status"])
    WORKER_SECONDS = Histogram("inferlens_worker_processing_seconds", "Worker processing", ["operation", "status"])
    WORKER_ERRORS = Counter("inferlens_worker_errors_total", "Worker errors", ["error_type"])
    DEAD_LETTERS = Counter("inferlens_dead_letters_total", "Dead letters", ["error_type"])
    REDACTIONS = Counter("inferlens_pii_redactions_total", "PII redactions", ["operation"])
    REPLAYS = Counter("inferlens_replays_total", "Replays", ["status"])
    COMPARISONS = Counter("inferlens_comparisons_total", "Comparisons", ["status"])
except Exception:  # metrics are optional and must not affect requests
    def generate_latest():
        return b""
    CONTENT_TYPE_LATEST = "text/plain"
    REQUESTS = ERRORS = CANCELLATIONS = DURATION = TTFT = INPUT_TOKENS = OUTPUT_TOKENS = COST = RETRIES = FALLBACKS = REDIS = WORKER_SECONDS = WORKER_ERRORS = DEAD_LETTERS = REDACTIONS = REPLAYS = COMPARISONS = None


def _call(metric, method: str, *args) -> None:
    with suppress(Exception):
        if metric is not None:
            getattr(metric, method)(*args)


def _label(metric, *labels):
    try:
        return metric.labels(*labels) if metric is not None else None
    except Exception:
        return None


def record_request(*, provider: str, model: str, status: str, operation: str, latency_ms: int, ttft_ms: int | None, input_tokens: int, output_tokens: int, cost: float, error_type: str | None = None, retry_count: int = 0, fallback_provider: str | None = None) -> None:
    _call(_label(REQUESTS, provider, model, status, operation), "inc")
    if error_type: _call(_label(ERRORS, provider, model, error_type), "inc")
    if status == "cancelled": _call(_label(CANCELLATIONS, provider, model), "inc")
    _call(_label(DURATION, provider, model, status), "observe", max(latency_ms, 0) / 1000)
    if ttft_ms is not None: _call(_label(TTFT, provider, model), "observe", max(ttft_ms, 0) / 1000)
    _call(_label(INPUT_TOKENS, provider, model), "inc", max(input_tokens, 0))
    _call(_label(OUTPUT_TOKENS, provider, model), "inc", max(output_tokens, 0))
    _call(_label(COST, provider, model), "inc", max(cost, 0))
    if retry_count: _call(_label(RETRIES, provider, model, error_type or "retry"), "inc", retry_count)
    if fallback_provider: _call(_label(FALLBACKS, provider, model), "inc")
