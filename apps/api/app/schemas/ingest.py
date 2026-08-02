from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SpanEvent(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    status: str = "ok"
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class StreamEventIn(BaseModel):
    sequence_number: int
    event_type: str
    delta_text: str = ""


class InferenceEventIn(BaseModel):
    event_id: str
    trace_id: str
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 800
    stream: bool = True
    status: str
    latency_ms: int | None = None
    time_to_first_token_ms: int | None = None
    tokens_per_second: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_input_cost: float = 0
    estimated_output_cost: float = 0
    estimated_total_cost: float = 0
    input_preview: str = ""
    output_preview: str = ""
    error_type: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    retryable: bool = False
    retry_count: int = 0
    fallback_provider: str | None = None
    routing_strategy: str | None = None
    routing_history_json: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str | None = None
    first_token_at: datetime | None = None
    completed_at: datetime | None = None
    content_captured: bool = False
    otel_trace_id: str | None = None
    otel_root_span_id: str | None = None
    otel_instrumented_at: datetime | None = None
    request_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    safe_metadata_json: dict[str, Any] = Field(default_factory=dict)
    spans: list[SpanEvent] = Field(default_factory=list)
    stream_events: list[StreamEventIn] = Field(default_factory=list)
    replayed_from_trace_id: str | None = None
    original_trace_id: str | None = None
    comparison_run_id: UUID | None = None


class IngestAccepted(BaseModel):
    status: str = "accepted"
    event_id: str
