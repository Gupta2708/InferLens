from app.config import get_settings
from app.llm.base import ChatMessage, LLMRequest
from app.observability.logger import ObservabilityLogger


def test_snapshot_omits_content_without_capture(monkeypatch):
    monkeypatch.setenv("CONTENT_CAPTURE_ENABLED", "false")
    get_settings.cache_clear()
    logger = ObservabilityLogger(None, LLMRequest("mock", "mock-fast", [ChatMessage("user", "secret@example.com")]))
    snapshot, _ = logger.snapshot()
    assert "messages" not in snapshot
    get_settings.cache_clear()


def test_snapshot_redacts_content_when_capture_enabled(monkeypatch):
    monkeypatch.setenv("CONTENT_CAPTURE_ENABLED", "true")
    get_settings.cache_clear()
    logger = ObservabilityLogger(None, LLMRequest("mock", "mock-fast", [ChatMessage("user", "secret@example.com")]))
    snapshot, redactions = logger.snapshot()
    assert "secret@example.com" not in snapshot["messages"][0]["content"]
    assert redactions
    get_settings.cache_clear()
