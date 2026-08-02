import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from app.db.session import Base


class GUID(TypeDecorator):
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class JSONCompat(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


def now_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(200), default="New conversation", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True, nullable=False)
    created_at: Mapped[datetime] = now_col()
    updated_at: Mapped[datetime] = now_col()
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("conversations.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), index=True)
    model: Mapped[str | None] = mapped_column(String(128), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = now_col()
    updated_at: Mapped[datetime] = now_col()

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    input_cost_per_1k_tokens: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    output_cost_per_1k_tokens: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[datetime] = now_col()
    updated_at: Mapped[datetime] = now_col()

    __table_args__ = (UniqueConstraint("provider", "model", name="uq_provider_model"),)


class InferenceTrace(Base):
    __tablename__ = "inference_traces"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    parent_trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    replayed_from_trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    comparison_run_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    otel_trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    otel_root_span_id: Mapped[str | None] = mapped_column(String(32))
    otel_instrumented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now_col()


class InferenceSpan(Base):
    __tablename__ = "inference_spans"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    span_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSONCompat, default=dict, nullable=False)
    created_at: Mapped[datetime] = now_col()


class InferenceLog(Base):
    __tablename__ = "inference_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=800, nullable=False)
    stream: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, index=True)
    time_to_first_token_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_per_second: Mapped[float | None] = mapped_column(Float)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_input_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    estimated_output_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    estimated_total_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    input_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(64), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(64), index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(64), index=True)
    routing_strategy: Mapped[str | None] = mapped_column(String(64))
    routing_history_json: Mapped[list] = mapped_column(JSONCompat, default=list, nullable=False)
    finish_reason: Mapped[str | None] = mapped_column(String(64), index=True)
    first_token_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_captured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    request_snapshot_json: Mapped[dict] = mapped_column(JSONCompat, default=dict, nullable=False)
    safe_metadata_json: Mapped[dict] = mapped_column(JSONCompat, default=dict, nullable=False)
    created_at: Mapped[datetime] = now_col()

    __table_args__ = (Index("ix_inference_logs_created_at", "created_at"),)


class StreamEvent(Base):
    __tablename__ = "stream_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    delta_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = now_col()


class ProviderError(Base):
    __tablename__ = "provider_errors"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    error_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = now_col()


class PiiRedactionEvent(Base):
    __tablename__ = "pii_redaction_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    pii_type: Mapped[str] = mapped_column(String(64), nullable=False)
    redacted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = now_col()


class IngestionEvent(Base):
    __tablename__ = "ingestion_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONCompat, default=dict, nullable=False)
    created_at: Mapped[datetime] = now_col()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("event_id", name="uq_ingestion_events_event_id"),)


class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONCompat, default=dict, nullable=False)
    created_at: Mapped[datetime] = now_col()
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(64), index=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComparisonRun(Base):
    __tablename__ = "comparison_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    context_mode: Mapped[str] = mapped_column(String(16), default="recent", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    created_at: Mapped[datetime] = now_col()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComparisonResult(Base):
    __tablename__ = "comparison_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    comparison_run_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    time_to_first_token_ms: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_total_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    output_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(64), index=True)
    error_category: Mapped[str | None] = mapped_column(String(64), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finish_reason: Mapped[str | None] = mapped_column(String(64), index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(64))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now_col()


Index("ix_logs_provider_model_created", InferenceLog.provider, InferenceLog.model, InferenceLog.created_at)
Index("ix_logs_status_created", InferenceLog.status, InferenceLog.created_at)
Index("ix_spans_trace_created", InferenceSpan.trace_id, InferenceSpan.created_at)
Index("ix_stream_trace_sequence", StreamEvent.trace_id, StreamEvent.sequence_number)
