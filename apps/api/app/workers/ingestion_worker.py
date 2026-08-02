import json
import signal
import time
from contextlib import suppress

from redis import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy import inspect

from app.config import get_settings
from app.db import models
from app.db.session import SessionLocal, engine
from app.llm.errors import normalize_exception
from app.observability.metrics import WORKER_ERRORS, WORKER_SECONDS
from app.observability.telemetry import configure_telemetry, shutdown_telemetry, span
from app.observability.trace_context import message_trace_context
from app.services.ingestion_service import process_ingestion_event
from app.workers.dead_letter import move_to_dead_letter

_running = True


def ensure_group(redis: Redis) -> None:
    try: redis.xgroup_create(get_settings().ingestion_stream, get_settings().worker_group, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc): raise


def stop_worker(*_args) -> None:
    global _running; _running = False


def _process(redis: Redis, consumer: str, redis_id: str, fields: dict) -> None:
    started = time.perf_counter(); event_id = fields.get("event_id", "unknown"); payload = json.loads(fields.get("payload", "{}")); db = SessionLocal()
    try:
        # Context is scoped to this message; no worker job can inherit a prior job's context.
        with message_trace_context(payload):
            with span("worker.consume", {"trace_id": payload.get("trace_id", "unknown")}):
                process_ingestion_event(db, event_id, payload)
        redis.xack(get_settings().ingestion_stream, get_settings().worker_group, redis_id)
        if WORKER_SECONDS: WORKER_SECONDS.labels("consume", "success").observe(time.perf_counter() - started)
    except Exception as exc:
        db.rollback(); error = normalize_exception(exc)
        record = db.query(models.IngestionEvent).filter_by(event_id=event_id).first()
        retries = (record.retry_count + 1) if record else get_settings().worker_retry_limit
        if record:
            record.retry_count = retries; record.status = "failed"; db.commit()
        if retries >= get_settings().worker_retry_limit:
            move_to_dead_letter(db, redis, event_id, payload, error.safe_message, retries)
            redis.xack(get_settings().ingestion_stream, get_settings().worker_group, redis_id)
        if WORKER_ERRORS: WORKER_ERRORS.labels(error.category).inc()
        if WORKER_SECONDS: WORKER_SECONDS.labels("consume", "error").observe(time.perf_counter() - started)
    finally:
        db.close()


def _recover_stale(redis: Redis, consumer: str) -> None:
    with suppress(Exception):
        result = redis.xautoclaim(get_settings().ingestion_stream, get_settings().worker_group, consumer, get_settings().worker_stale_claim_ms, "0-0", count=10)
        for redis_id, fields in result[1] if len(result) > 1 else []:
            _process(redis, consumer, redis_id, fields)


def run_forever() -> None:
    global _running
    settings = get_settings(); wait_for_schema(); configure_telemetry("inferlens-worker")
    for name in ("SIGINT", "SIGTERM"):
        with suppress(Exception): signal.signal(getattr(signal, name), stop_worker)
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=10); ensure_group(redis); consumer = f"worker-{int(time.time())}"
    while _running:
        _recover_stale(redis, consumer)
        try: messages = redis.xreadgroup(settings.worker_group, consumer, {settings.ingestion_stream: ">"}, count=10, block=1000)
        except RedisTimeoutError: continue
        for _, entries in messages:
            for redis_id, fields in entries:
                if not _running: break
                _process(redis, consumer, redis_id, fields)
    shutdown_telemetry()


def wait_for_schema() -> None:
    while _running:
        try:
            inspector = inspect(engine)
            if inspector.has_table("ingestion_events") and inspector.has_table("inference_logs"): return
        except Exception: pass
        time.sleep(2)


if __name__ == "__main__": run_forever()
