import json
import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.llm.errors import sanitize_error_message
from app.observability.telemetry import current_ids


class SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = sanitize_error_message(str(record.getMessage()))
            record.args = ()
        except Exception:
            pass
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = current_ids()
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname, "service": "inferlens-api", "environment": get_settings().app_env, "event": record.name, "message": sanitize_error_message(record.getMessage()), "otel_trace_id": trace_id, "span_id": span_id})


def configure_logging() -> None:
    root = logging.getLogger(); root.setLevel(get_settings().log_level.upper())
    for handler in root.handlers:
        handler.addFilter(SecretFilter())
        if get_settings().app_env.lower() in {"production", "prod"}:
            handler.setFormatter(JsonFormatter())
