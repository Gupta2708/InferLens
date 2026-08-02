from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProviderTarget(BaseModel):
    provider: str
    model: str


class ComparisonCreate(BaseModel):
    prompt: str = Field(min_length=1)
    conversation_id: UUID | None = None
    source_message_id: UUID | None = None
    context_mode: str = "recent"
    temperature: float = 0.7
    max_tokens: int = 800
    targets: list[ProviderTarget]


class ComparisonResultOut(BaseModel):
    id: UUID
    comparison_run_id: UUID
    trace_id: str
    provider: str
    model: str
    status: str
    latency_ms: int | None
    time_to_first_token_ms: int | None
    total_tokens: int
    estimated_total_cost: float
    output_preview: str
    error_type: str | None
    error_category: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None
    retry_count: int = 0
    fallback_provider: str | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ComparisonRunOut(BaseModel):
    id: UUID
    prompt: str
    context_mode: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    results: list[ComparisonResultOut] = []

    model_config = {"from_attributes": True}
