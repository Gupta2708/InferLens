import json
from datetime import datetime, timezone
from typing import Any

from redis import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import models
from app.observability.redaction import redact_event_payload
from app.observability.trace_context import inject_trace_context
from app.observability.metrics import REDIS, REDACTIONS


def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "hex"):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def enqueue(self, event: dict) -> str:
        event = inject_trace_context(json.loads(json.dumps(event, default=_json_safe)))
        event_id = event["event_id"]
        existing = self.db.query(models.IngestionEvent).filter_by(event_id=event_id).first()
        if existing:
            return event_id
        self.db.add(
            models.IngestionEvent(
                event_id=event_id,
                trace_id=event["trace_id"],
                event_type="inference",
                status="pending",
                retry_count=0,
                payload_json=event,
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return event_id
        try:
            redis = Redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.1,
                socket_timeout=0.1,
            )
            redis.xadd(
                self.settings.ingestion_stream,
                {"event_id": event_id, "payload": json.dumps(event, default=_json_safe)},
            )
            if REDIS:
                REDIS.labels("success").inc()
        except Exception:
            if REDIS:
                REDIS.labels("fallback").inc()
            process_ingestion_event(self.db, event_id, event)
        return event_id


def process_ingestion_event(db: Session, event_id: str, payload: dict) -> None:
    clean, redactions = redact_event_payload(payload)
    if db.query(models.InferenceLog).filter_by(trace_id=clean["trace_id"]).first():
        _mark_processed(db, event_id)
        return

    trace = models.InferenceTrace(
        trace_id=clean["trace_id"],
        conversation_id=clean.get("conversation_id"),
        message_id=clean.get("message_id"),
        replayed_from_trace_id=clean.get("replayed_from_trace_id"),
        comparison_run_id=clean.get("comparison_run_id"),
        status=clean.get("status", "completed"),
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        duration_ms=clean.get("latency_ms"),
        otel_trace_id=clean.get("otel_trace_id"),
        otel_root_span_id=clean.get("otel_root_span_id"),
        otel_instrumented_at=_parse_dt(clean.get("otel_instrumented_at")),
        original_trace_id=clean.get("original_trace_id"),
        completed_at=_parse_dt(clean.get("completed_at")),
    )
    db.add(trace)
    db.add(
        models.InferenceLog(
            trace_id=clean["trace_id"],
            conversation_id=clean.get("conversation_id"),
            message_id=clean.get("message_id"),
            provider=clean["provider"],
            model=clean["model"],
            temperature=clean.get("temperature", 0.7),
            max_tokens=clean.get("max_tokens", 800),
            stream=clean.get("stream", True),
            status=clean.get("status", "completed"),
            latency_ms=clean.get("latency_ms"),
            time_to_first_token_ms=clean.get("time_to_first_token_ms"),
            tokens_per_second=clean.get("tokens_per_second"),
            input_tokens=clean.get("input_tokens", 0),
            output_tokens=clean.get("output_tokens", 0),
            total_tokens=clean.get("total_tokens", 0),
            estimated_input_cost=clean.get("estimated_input_cost", 0),
            estimated_output_cost=clean.get("estimated_output_cost", 0),
            estimated_total_cost=clean.get("estimated_total_cost", 0),
            input_preview=clean.get("input_preview", ""),
            output_preview=clean.get("output_preview", ""),
            error_type=clean.get("error_type"),
            error_message=clean.get("error_message"),
            retryable=clean.get("retryable", False),
            error_category=clean.get("error_category") or clean.get("error_type"),
            retry_count=clean.get("retry_count", 0),
            fallback_provider=clean.get("fallback_provider"),
            routing_strategy=clean.get("routing_strategy"),
            routing_history_json=clean.get("routing_history_json", []),
            finish_reason=clean.get("finish_reason"),
            first_token_at=_parse_dt(clean.get("first_token_at")),
            completed_at=_parse_dt(clean.get("completed_at")),
            content_captured=clean.get("content_captured", False),
            request_snapshot_json=clean.get("request_snapshot_json", {}),
            safe_metadata_json=clean.get("safe_metadata_json", {}),
        )
    )
    for span in clean.get("spans", []):
        db.add(
            models.InferenceSpan(
                trace_id=clean["trace_id"],
                span_id=span["span_id"],
                parent_span_id=span.get("parent_span_id"),
                name=span["name"],
                status=span.get("status", "ok"),
                start_time=_parse_dt(span.get("start_time")) or datetime.now(timezone.utc),
                end_time=_parse_dt(span.get("end_time")),
                duration_ms=span.get("duration_ms"),
                metadata_json=span.get("metadata_json", {}),
            )
        )
    worker_time = datetime.now(timezone.utc)
    db.add(
        models.InferenceSpan(
            trace_id=clean["trace_id"],
            span_id=f"span_worker_{event_id[-16:]}",
            name="worker_persisted",
            status="ok",
            start_time=worker_time,
            end_time=worker_time,
            duration_ms=0,
            metadata_json={"event_id": event_id},
        )
    )
    for stream_event in clean.get("stream_events", []):
        db.add(
            models.StreamEvent(
                trace_id=clean["trace_id"],
                sequence_number=stream_event["sequence_number"],
                event_type=stream_event["event_type"],
                delta_text=stream_event.get("delta_text", ""),
            )
        )
    if clean.get("error_type"):
        db.add(
            models.ProviderError(
                trace_id=clean["trace_id"],
                provider=clean["provider"],
                model=clean["model"],
                error_type=clean["error_type"],
                error_message=clean.get("error_message") or "",
                retryable=clean.get("retryable", False),
            )
        )
    for redaction in redactions:
        db.add(
            models.PiiRedactionEvent(
                trace_id=clean["trace_id"],
                field_name=redaction.field_name,
                pii_type=redaction.pii_type,
                redacted_count=redaction.redacted_count,
            )
        )
        if REDACTIONS:
            REDACTIONS.labels("persistence").inc(redaction.redacted_count)
    _mark_processed(db, event_id)
    db.commit()


def _mark_processed(db: Session, event_id: str) -> None:
    record = db.query(models.IngestionEvent).filter_by(event_id=event_id).first()
    if record:
        record.status = "processed"
        record.processed_at = datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None
