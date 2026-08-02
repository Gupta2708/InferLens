from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Optional, TypeVar

from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.base import LLMChunk, LLMRequest, LLMResponse, Provider
from app.llm.errors import CircuitOpenError, ProviderModelInvalidError, ProviderNotFoundError, UserCancelledError, normalize_exception
from app.llm.providers.gemini_provider import GeminiProvider
from app.llm.providers.mock_provider import MockProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.registry import ProviderRegistry
from app.llm.resilience import RoutingAttempt, RoutingResult, breaker, fallback_chain, retry_delay
from app.services.provider_catalog import DEFAULT_PROVIDER_CONFIGS, configured_real_providers, default_model_for_provider, effective_mock_mode, normalize_model_alias, provider_model_exists

T = TypeVar("T")


class LLMGateway:
    def __init__(self, db: Optional[Session] = None, registry: ProviderRegistry | None = None) -> None:
        self.settings = get_settings()
        self.db = db
        self.registry = registry or ProviderRegistry([MockProvider(), OpenAIProvider(), GeminiProvider()])
        self.providers: dict[str, Provider] = {name: self.registry.get(name) for name in self.registry.names()}  # legacy public property

    def resolve_provider(self, provider: str | None) -> str:
        real = configured_real_providers(self.settings)
        if effective_mock_mode(self.settings):
            resolved = "mock"
        elif provider in real:
            resolved = provider
        elif len(real) == 1:
            resolved = next(iter(real))
        elif self.settings.default_provider in real:
            resolved = self.settings.default_provider
        else:
            resolved = "openai" if "openai" in real else "gemini"
        if resolved not in self.providers:
            raise ProviderNotFoundError(f"Provider {resolved} is not configured")
        return resolved

    def resolve_model(self, provider: str, model: str | None) -> str:
        if provider == "mock":
            return model if model and model.startswith("mock") else "mock-fast"
        if model:
            return normalize_model_alias(provider, model)
        return default_model_for_provider(provider) or self.settings.default_model

    def _is_valid_provider_model(self, provider: str, model: str) -> bool:
        return provider_model_exists(self.db, provider, model)

    def _prepare(self, request: LLMRequest) -> None:
        provider = self.resolve_provider(request.provider)
        request.provider = provider
        request.model = self.resolve_model(provider, request.model)
        if not self._is_valid_provider_model(request.provider, request.model):
            raise ProviderModelInvalidError(f"Model {request.model} is not valid for provider {request.provider}")

    async def _attempt(self, request: LLMRequest, call: Callable[[Provider], Awaitable[T]]) -> tuple[T, RoutingResult]:
        self._prepare(request)
        routing = RoutingResult()
        candidates = [request.provider, *fallback_chain(request.provider, configured_real_providers(self.settings))]
        final_error: Exception | None = None
        for index, provider_name in enumerate(candidates):
            if provider_name not in self.providers:
                continue
            provider_model = request.model if provider_name == request.provider else self.resolve_model(provider_name, None)
            if not self._is_valid_provider_model(provider_name, provider_model):
                continue
            request.provider, request.model = provider_name, provider_model
            if not breaker.allow(provider_name):
                error = CircuitOpenError(f"Provider {provider_name} circuit is open")
                routing.attempts.append(RoutingAttempt(provider_name, 0, "skipped", error.category, "open"))
                final_error = error
                continue
            for attempt in range(self.settings.provider_max_retries + 1):
                if request.cancellation_event is not None and request.cancellation_event.is_set():
                    raise UserCancelledError("Request cancelled by client")
                try:
                    value = await call(self.providers[provider_name])
                    breaker.success(provider_name)
                    routing.attempts.append(RoutingAttempt(provider_name, attempt, "success"))
                    request.metadata["routing_history"] = routing.metadata()
                    request.metadata["retry_count"] = sum(item.attempt for item in routing.attempts)
                    request.metadata["fallback_provider"] = provider_name if index else None
                    return value, routing
                except Exception as exc:
                    error = normalize_exception(exc, provider_name)
                    final_error = error
                    circuit = breaker.failure(provider_name, error)
                    routing.attempts.append(RoutingAttempt(provider_name, attempt, "failed", error.category, circuit))
                    if not error.retryable or error.category == "client_cancelled" or attempt >= self.settings.provider_max_retries:
                        break
                    await retry_delay(attempt)
        assert final_error is not None
        raise final_error

    async def generate(self, request: LLMRequest) -> LLMResponse:
        response, routing = await self._attempt(request, lambda provider: provider.generate(request))
        response.safe_metadata = {**response.safe_metadata, "routing_history": routing.metadata()}
        return response

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        self._prepare(request)
        # A stream may only be retried before a byte/token reaches the caller.
        candidates = [request.provider, *fallback_chain(request.provider, configured_real_providers(self.settings))]
        final_error: Exception | None = None
        routing = RoutingResult()
        for candidate_index, provider_name in enumerate(candidates):
            if provider_name not in self.providers or not breaker.allow(provider_name):
                continue
            request.provider = provider_name
            request.model = self.resolve_model(provider_name, request.model if candidate_index == 0 else None)
            emitted = False
            for attempt in range(self.settings.provider_max_retries + 1):
                try:
                    async for chunk in self.providers[provider_name].stream(request):
                        emitted = True
                        yield chunk
                    breaker.success(provider_name)
                    routing.attempts.append(RoutingAttempt(provider_name, attempt, "success"))
                    request.metadata["routing_history"] = routing.metadata()
                    request.metadata["retry_count"] = sum(item.attempt for item in routing.attempts)
                    request.metadata["fallback_provider"] = provider_name if candidate_index else None
                    return
                except Exception as exc:
                    error = normalize_exception(exc, provider_name)
                    final_error = error
                    circuit = breaker.failure(provider_name, error)
                    routing.attempts.append(RoutingAttempt(provider_name, attempt, "failed", error.category, circuit))
                    if emitted or not error.retryable or error.category == "client_cancelled" or attempt >= self.settings.provider_max_retries:
                        raise error
                    await retry_delay(attempt)
        raise final_error or ProviderNotFoundError("No eligible provider is available")

    def available_models(self) -> list[dict]:
        return [{"provider": config["provider"], "model": config["model"], "enabled": config["enabled"], "supports_streaming": config["supports_streaming"]} for config in DEFAULT_PROVIDER_CONFIGS]

    async def health(self) -> dict[str, dict]:
        return await self.registry.health()
