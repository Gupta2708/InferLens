import pytest

from app.config import get_settings
from app.llm.base import ChatMessage, LLMRequest
from app.llm.errors import ProviderModelInvalidError, ProviderServerError
from app.llm.gateway import LLMGateway
from app.llm.resilience import breaker


@pytest.mark.asyncio
async def test_gateway_uses_mock_mode_for_real_provider_request():
    response = await LLMGateway().generate(
        LLMRequest("openai", "gpt-4.1-mini", [ChatMessage("user", "hello")], stream=False)
    )
    assert response.provider == "mock"
    assert response.model == "mock-fast"


@pytest.mark.asyncio
async def test_gateway_automatically_uses_mock_without_real_keys(monkeypatch):
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    response = await LLMGateway().generate(
        LLMRequest("openai", "gpt-4.1-mini", [ChatMessage("user", "hello")], stream=False)
    )
    assert response.provider == "mock"
    assert response.model == "mock-fast"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_gateway_uses_only_configured_real_provider(monkeypatch):
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    gateway = LLMGateway()
    assert gateway.resolve_provider("gemini") == "openai"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_gateway_honors_explicit_mock_with_real_key(monkeypatch):
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    response = await LLMGateway().generate(
        LLMRequest("mock", "mock-fast", [ChatMessage("user", "hello")], stream=False)
    )
    assert response.provider == "mock"
    assert response.model == "mock-fast"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_gateway_mock_error_does_not_fall_back_to_real_provider(monkeypatch):
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PROVIDER_RETRY_BASE_MS", "1")
    get_settings.cache_clear(); breaker.states.clear()
    request = LLMRequest("mock", "mock-error", [ChatMessage("user", "hello")], stream=False)

    with pytest.raises(ProviderServerError) as exc_info:
        await LLMGateway().generate(request)

    assert exc_info.value.provider == "mock"
    assert request.provider == "mock"
    assert request.model == "mock-error"
    get_settings.cache_clear(); breaker.states.clear()


@pytest.mark.asyncio
async def test_gateway_rejects_invalid_provider_model_combo(monkeypatch):
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    gateway = LLMGateway()

    with pytest.raises(ProviderModelInvalidError):
        await gateway.generate(
            LLMRequest("gemini", "mock-fast", [ChatMessage("user", "hello")], stream=False)
        )

    get_settings.cache_clear()


def test_gateway_resolves_legacy_gemini_alias(monkeypatch):
    monkeypatch.setenv("LLM_MOCK_MODE", "false")
    get_settings.cache_clear()
    gateway = LLMGateway()

    assert gateway.resolve_model("gemini", "gemini-2.0-flash") == "gemini-2.5-flash"
    assert gateway.resolve_model("gemini", "gemini-flash-latest") == "gemini-2.5-flash"

    get_settings.cache_clear()
