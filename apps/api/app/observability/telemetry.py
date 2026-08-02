"""Optional OTLP bootstrap; all failures degrade to no-op tracing."""
from contextlib import suppress

from app.config import get_settings

_provider = None


def configure_telemetry(service_name: str) -> None:
    global _provider
    settings = get_settings()
    if not settings.otel_enabled or not settings.otel_exporter_otlp_endpoint:
        return
    with suppress(Exception):
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, headers=_headers(settings.otel_exporter_otlp_headers))))
        trace.set_tracer_provider(provider)
        _provider = provider


def _headers(value: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in value.split(",") if "=" in part)


def shutdown_telemetry() -> None:
    with suppress(Exception):
        if _provider: _provider.shutdown()


def current_ids() -> tuple[str | None, str | None]:
    with suppress(Exception):
        from opentelemetry import trace
        context = trace.get_current_span().get_span_context()
        if context and context.is_valid:
            return f"{context.trace_id:032x}", f"{context.span_id:016x}"
    return None, None


def span(name: str, attributes: dict | None = None):
    """Returns a no-op-compatible context manager."""
    try:
        from opentelemetry import trace
        return trace.get_tracer("inferlens").start_as_current_span(name, attributes=attributes or {})
    except Exception:
        from contextlib import nullcontext
        return nullcontext()
