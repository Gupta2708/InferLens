from app.observability.trace_context import extract_trace_context, inject_trace_context, message_trace_context


def test_trace_context_is_non_destructive_and_malformed_is_safe():
    payload = {"event_id": "evt", "trace_id": "trace", "business": "kept"}
    injected = inject_trace_context(payload)
    assert injected["business"] == "kept"
    extract_trace_context({"trace_context": {"traceparent": "bad"}})
    with message_trace_context({"trace_context": {"traceparent": "bad"}}):
        pass
