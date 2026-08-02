import pytest

from app.config import get_settings
from app.llm.base import ChatMessage, LLMRequest
from app.llm.errors import ProviderTimeoutError
from app.llm.gateway import LLMGateway
from app.llm.registry import ProviderRegistry
from app.llm.resilience import breaker
from app.llm.resilience import fallback_chain


class FailingProvider:
    provider = "mock"
    async def generate(self, request): raise ProviderTimeoutError("temporary")
    async def stream(self, request):
        if False: yield None
        raise ProviderTimeoutError("temporary")
    async def health_check(self): return {"status": "healthy"}
    def metadata(self): return {}


@pytest.mark.asyncio
async def test_retry_history_is_recorded(monkeypatch):
    monkeypatch.setenv("PROVIDER_MAX_RETRIES", "1")
    from app.config import get_settings
    get_settings.cache_clear(); breaker.states.clear()
    gateway = LLMGateway(registry=ProviderRegistry([FailingProvider()]))
    with pytest.raises(ProviderTimeoutError):
        await gateway.generate(LLMRequest("mock", "mock-fast", [ChatMessage("user", "hello")], stream=False))
    assert breaker.states["mock"].failures == 2
    get_settings.cache_clear()


def test_default_real_provider_fallbacks_are_reciprocal(monkeypatch):
    monkeypatch.setenv("PROVIDER_FALLBACKS", "{}")
    get_settings.cache_clear()
    assert fallback_chain("openai", {"openai", "gemini"}) == ["gemini"]
    assert fallback_chain("gemini", {"openai", "gemini"}) == ["openai"]
    assert fallback_chain("openai", {"openai"}) == []
    get_settings.cache_clear()
