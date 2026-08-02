from contextlib import contextmanager, suppress


def inject_trace_context(payload: dict) -> dict:
    envelope = dict(payload)
    headers: dict[str, str] = {}
    with suppress(Exception):
        from opentelemetry.propagate import inject
        inject(headers)
    if headers:
        envelope["trace_context"] = {key: headers[key] for key in ("traceparent", "tracestate") if key in headers}
    return envelope


def extract_trace_context(payload: dict):
    headers = payload.get("trace_context")
    if not isinstance(headers, dict):
        return None
    safe = {key: value for key, value in headers.items() if key in {"traceparent", "tracestate"} and isinstance(value, str) and len(value) <= 512}
    with suppress(Exception):
        from opentelemetry.propagate import extract
        return extract(safe)
    return None


@contextmanager
def message_trace_context(payload: dict):
    """Attach extracted context only for one worker message, then always detach it."""
    context = extract_trace_context(payload)
    token = None
    with suppress(Exception):
        from opentelemetry.context import attach
        if context is not None:
            token = attach(context)
    try:
        yield
    finally:
        with suppress(Exception):
            if token is not None:
                from opentelemetry.context import detach
                detach(token)
