import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.base import LLMRequest, LLMResponse
from app.llm.cost import estimate_cost
from app.llm.errors import NormalizedError, sanitize_error_message
from app.observability.metadata import safe_metadata
from app.observability.metrics import record_request
from app.observability.redaction import redact_messages, redact_text
from app.observability.spans import SpanRecord
from app.observability.telemetry import current_ids
from app.observability.trace import new_trace_id
from app.services.ingestion_service import IngestionService


class ObservabilityLogger:
    """Records InferLens' primary trace without making logging a request dependency."""
    def __init__(self, db: Session, request: LLMRequest, conversation_id: Any = None, message_id: Any = None, trace_id: str | None = None, replayed_from_trace_id: str | None = None, comparison_run_id: Any = None):
        self.db, self.request, self.conversation_id, self.message_id = db, request, conversation_id, message_id
        self.trace_id = trace_id or new_trace_id()
        self.replayed_from_trace_id, self.comparison_run_id = replayed_from_trace_id, comparison_run_id
        self.started = time.perf_counter(); self.started_at = datetime.now(timezone.utc)
        self.spans: list[SpanRecord] = []; self.stream_events: list[dict] = []
        self.first_token_ms: int | None = None; self.first_token_at: datetime | None = None

    def span(self, name: str, status: str = "ok", **metadata: Any) -> None:
        item = SpanRecord(name=name); item.finish(status=status, **safe_metadata(metadata)); self.spans.append(item)

    def record_chunk(self, sequence_number: int, delta_text: str) -> None:
        if self.first_token_ms is None:
            self.first_token_ms, self.first_token_at = self.elapsed_ms(), datetime.now(timezone.utc)
            self.span("stream.first_token", sequence_number=sequence_number)
        # Deltas are trace content, not application logs. Store only when capture was explicitly enabled.
        if get_settings().content_capture_enabled:
            clean, _ = redact_text(delta_text, "stream_event")
            self.stream_events.append({"sequence_number": sequence_number, "event_type": "token", "delta_text": clean})

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)

    def snapshot(self) -> tuple[dict, list]:
        base = {"provider": self.request.provider, "model": self.request.model, "temperature": self.request.temperature, "max_tokens": self.request.max_tokens, "stream": self.request.stream, "mock_scenario": self.request.mock_scenario}
        if not get_settings().content_capture_enabled:
            return base, []
        messages, redactions = redact_messages([{"role": message.role, "content": message.content} for message in self.request.messages])
        base["messages"] = messages
        return base, redactions

    def finish(self, status: str, response: LLMResponse | None = None, content: str = "", error: NormalizedError | None = None, error_type: str | None = None, error_message: str | None = None, retryable: bool = False) -> str:
        latency_ms = self.elapsed_ms(); settings = get_settings(); completed_at = datetime.now(timezone.utc)
        input_tokens = response.input_tokens if response else self._input_tokens()
        output_tokens = response.output_tokens if response else max(0, len(content.split()))
        total_tokens = response.total_tokens if response else input_tokens + output_tokens
        input_cost, output_cost, total_cost = estimate_cost(self.request.provider, self.request.model, input_tokens, output_tokens)
        if status in {"completed", "cancelled"}: self.span("stream.consume" if self.request.stream else "provider.generate", status=status)
        self.span("ingestion.redis_publish", status=status)
        snapshot, snapshot_redactions = self.snapshot()
        normalized_category = error.category if error else error_type
        safe_error = error.safe_message if error else sanitize_error_message(error_message or "")
        is_retryable = error.retryable if error else retryable
        capture = settings.content_capture_enabled
        input_preview, output_preview = "", ""
        if capture:
            input_preview, _ = redact_text("\n".join(f"{m.role}: {m.content}" for m in self.request.messages), "input_preview")
            output_preview, _ = redact_text(content[:settings.content_capture_preview_limit], "output_preview")
        otel_trace_id, otel_span_id = current_ids()
        routing = self.request.metadata.get("routing_history", [])
        retry_count = int(self.request.metadata.get("retry_count", 0) or 0)
        fallback_provider = self.request.metadata.get("fallback_provider")
        event = {
            "event_id": f"evt_{uuid.uuid4().hex}", "trace_id": self.trace_id, "conversation_id": self.conversation_id, "message_id": self.message_id,
            "provider": self.request.provider, "model": self.request.model, "temperature": self.request.temperature, "max_tokens": self.request.max_tokens, "stream": self.request.stream,
            "status": status, "latency_ms": latency_ms, "time_to_first_token_ms": self.first_token_ms, "tokens_per_second": round(output_tokens / max(latency_ms / 1000, 0.001), 2),
            "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens, "estimated_input_cost": input_cost, "estimated_output_cost": output_cost, "estimated_total_cost": total_cost,
            "input_preview": input_preview, "output_preview": output_preview, "error_type": normalized_category, "error_category": normalized_category, "error_message": safe_error or None, "retryable": is_retryable,
            "retry_count": retry_count, "fallback_provider": fallback_provider, "routing_strategy": "configured_fallback" if fallback_provider else "primary", "routing_history_json": routing,
            "finish_reason": response.finish_reason if response else None, "first_token_at": self.first_token_at, "completed_at": completed_at, "content_captured": capture,
            "request_snapshot_json": snapshot, "safe_metadata_json": safe_metadata(response.safe_metadata if response else {}),
            "otel_trace_id": otel_trace_id, "otel_root_span_id": otel_span_id, "otel_instrumented_at": completed_at if otel_trace_id else None,
            "spans": [{"span_id": span.span_id, "parent_span_id": span.parent_span_id, "name": span.name, "status": span.status, "start_time": span.start_time, "end_time": span.end_time, "duration_ms": span.duration_ms, "metadata_json": span.metadata_json} for span in self.spans],
            "stream_events": self.stream_events, "replayed_from_trace_id": self.replayed_from_trace_id, "original_trace_id": self.replayed_from_trace_id, "comparison_run_id": self.comparison_run_id,
        }
        try: IngestionService(self.db).enqueue(event)
        except Exception: pass
        record_request(provider=self.request.provider, model=self.request.model, status=status, operation="stream" if self.request.stream else "generate", latency_ms=latency_ms, ttft_ms=self.first_token_ms, input_tokens=input_tokens, output_tokens=output_tokens, cost=total_cost, error_type=normalized_category, retry_count=retry_count, fallback_provider=fallback_provider)
        return self.trace_id

    def _input_tokens(self) -> int:
        return max(1, sum(len(message.content.split()) for message in self.request.messages))
