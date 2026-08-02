from pydantic import BaseModel


class SummaryOut(BaseModel):
    total_requests: int
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    cancellation_rate: float
    total_tokens: int
    estimated_cost: float
    success_rate: float = 0
    p50_ttft_ms: float = 0
    p95_ttft_ms: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    retry_count: int = 0
    fallback_count: int = 0
    replay_count: int = 0
    comparison_count: int = 0
    worker_processing_latency_ms: float = 0
    dead_letter_count: int = 0
    pii_redaction_count: int = 0
