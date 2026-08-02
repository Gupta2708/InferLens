import json
from datetime import datetime, timezone

from redis import Redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import models
from app.llm.errors import normalize_exception
from app.observability.metrics import DEAD_LETTERS


def move_to_dead_letter(db: Session, redis: Redis, event_id: str, payload: dict, reason: str, retry_count: int = 0) -> None:
    settings = get_settings(); error = normalize_exception(Exception(reason))
    safe = {"event_id": event_id, "trace_id": payload.get("trace_id", "unknown"), "retry_count": retry_count, "error_category": error.category, "failure_timestamp": datetime.now(timezone.utc).isoformat(), "failure_summary": error.safe_message}
    redis.xadd(settings.dead_letter_stream, {"event_id": event_id, "payload": json.dumps(safe)})
    db.add(models.DeadLetterEvent(event_id=event_id, trace_id=safe["trace_id"], event_type="inference", failure_reason=error.safe_message, payload_json=safe, retry_count=retry_count, error_category=error.category, failed_at=datetime.now(timezone.utc)))
    event = db.query(models.IngestionEvent).filter_by(event_id=event_id).first()
    if event:
        event.status = "dead_lettered"; event.dead_lettered_at = datetime.now(timezone.utc)
    db.commit()
    if DEAD_LETTERS: DEAD_LETTERS.labels(error.category).inc()
