from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TraceReplayRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    without_context: bool = False
    edited_user_message: str | None = None
    mock_scenario: str | None = None


class TraceOut(BaseModel):
    trace_id: str
    status: str
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    otel: dict[str, Any] = Field(default_factory=dict)
    external_trace_url: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    spans: list[dict[str, Any]] = Field(default_factory=list)
    stream_events: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    redactions: list[dict[str, Any]] = Field(default_factory=list)
    replays: list[dict[str, Any]] = Field(default_factory=list)
