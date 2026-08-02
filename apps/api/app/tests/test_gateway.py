import pytest

from app.config import get_settings
from app.llm.base import ChatMessage, LLMRequest
from app.llm.errors import ProviderModelInvalidError
from app.llm.gateway import LLMGateway


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
