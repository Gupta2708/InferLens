from sqlalchemy.orm import Session

from app.db import models
from app.config import get_settings


class TraceService:
    def __init__(self, db: Session):
        self.db = db

    def get_trace(self, trace_id: str) -> dict:
        trace = self.db.query(models.InferenceTrace).filter_by(trace_id=trace_id).first()
        log = self.db.query(models.InferenceLog).filter_by(trace_id=trace_id).first()
        if not trace and not log:
            raise KeyError("trace_not_found")
        spans = self.db.query(models.InferenceSpan).filter_by(trace_id=trace_id).order_by(models.InferenceSpan.created_at).all()
        stream_events = self.db.query(models.StreamEvent).filter_by(trace_id=trace_id).order_by(models.StreamEvent.sequence_number).all()
        errors = self.db.query(models.ProviderError).filter_by(trace_id=trace_id).all()
        redactions = self.db.query(models.PiiRedactionEvent).filter_by(trace_id=trace_id).all()
        replays = self.db.query(models.InferenceTrace).filter_by(replayed_from_trace_id=trace_id).all()
        replay_logs = {
            row.trace_id: row
            for row in self.db.query(models.InferenceLog)
            .filter(models.InferenceLog.trace_id.in_([replay.trace_id for replay in replays] or [""]))
            .all()
        }
        return {
            "trace_id": trace_id,
            "status": (trace.status if trace else log.status),
            "conversation_id": trace.conversation_id if trace else log.conversation_id,
            "message_id": trace.message_id if trace else log.message_id,
            "otel": {"trace_id": trace.otel_trace_id if trace else None, "root_span_id": trace.otel_root_span_id if trace else None, "instrumented_at": trace.otel_instrumented_at if trace else None},
            "external_trace_url": _external_trace_url(trace.otel_trace_id if trace else None),
            "summary": {
                "provider": log.provider if log else None,
                "model": log.model if log else None,
                "latency_ms": log.latency_ms if log else None,
                "time_to_first_token_ms": log.time_to_first_token_ms if log else None,
                "tokens": log.total_tokens if log else 0,
                "cost": log.estimated_total_cost if log else 0,
                "input_preview": log.input_preview if log else "",
                "output_preview": log.output_preview if log else "",
                "error_type": log.error_type if log else None,
                "error_message": log.error_message if log else None,
                "safe_metadata": log.safe_metadata_json if log else {},
                "error_category": log.error_category if log else None,
                "retry_count": log.retry_count if log else 0,
                "fallback_provider": log.fallback_provider if log else None,
                "routing_strategy": log.routing_strategy if log else None,
                "routing_history": log.routing_history_json if log else [],
                "finish_reason": log.finish_reason if log else None,
                "content_captured": log.content_captured if log else False,
            },
            "spans": [_row_dict(s, ["id"]) for s in spans],
            "stream_events": [_row_dict(e, ["id"]) for e in stream_events],
            "errors": [_row_dict(e, ["id"]) for e in errors],
            "redactions": [_row_dict(r, ["id"]) for r in redactions],
            "replays": [
                {
                    "trace_id": replay.trace_id,
                    "status": replay.status,
                    "provider": replay_logs.get(replay.trace_id).provider if replay.trace_id in replay_logs else None,
                    "model": replay_logs.get(replay.trace_id).model if replay.trace_id in replay_logs else None,
                    "latency_ms": replay_logs.get(replay.trace_id).latency_ms if replay.trace_id in replay_logs else replay.duration_ms,
                    "created_at": replay.created_at,
                }
                for replay in replays
            ],
        }


def _row_dict(row, exclude: list[str]) -> dict:
    return {k: v for k, v in row.__dict__.items() if not k.startswith("_") and k not in exclude}


def _external_trace_url(otel_trace_id: str | None) -> str | None:
    template = get_settings().external_trace_url_template
    return template.replace("{trace_id}", otel_trace_id) if template and otel_trace_id else None
