import asyncio
from collections.abc import AsyncIterator

from app.config import get_settings
from app.llm.base import LLMChunk, LLMRequest, LLMResponse
from app.llm.errors import ProviderRateLimitError, ProviderServerError, ProviderTimeoutError, UserCancelledError


def _tokens(text: str) -> int:
    return max(1, len(text.split()))


class MockProvider:
    provider = "mock"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        await self._maybe_fail(request)
        if request.model == "mock-slow":
            await asyncio.sleep(0.45)
        prompt = request.messages[-1].content if request.messages else ""
        content = f"Mock response for: {prompt[:160]}"
        input_tokens = sum(_tokens(message.content) for message in request.messages)
        output_tokens = _tokens(content)
        return LLMResponse(
            content=content,
            provider="mock",
            model=request.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            safe_metadata={"mock": True, "scenario": request.mock_scenario or "normal"},
            provider_request_id=f"mock-{request.model}",
            finish_reason="stop",
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        await self._maybe_fail(request)
        prompt = request.messages[-1].content if request.messages else ""
        content = f"Mock streaming response for: {prompt[:160]}"
        delay = 0.45 if request.model == "mock-slow" else get_settings().mock_chunk_delay_ms / 1000
        for index, word in enumerate(content.split()):
            if request.cancellation_event is not None and request.cancellation_event.is_set():
                raise UserCancelledError("Mock request cancelled")
            if request.mock_scenario == "cancel_after_3" and index >= 3:
                raise UserCancelledError("Mock stream cancelled after 3 chunks")
            await asyncio.sleep(delay)
            yield LLMChunk(delta=(word + " "), sequence_number=index + 1)

    async def health_check(self) -> dict:
        return {"status": "healthy", "deterministic": True}

    def metadata(self) -> dict:
        return {"provider": self.provider, "supports_streaming": True, "models": ["mock-fast", "mock-slow", "mock-error"]}

    async def _maybe_fail(self, request: LLMRequest) -> None:
        scenario = "provider_error" if request.model == "mock-error" else request.mock_scenario
        if scenario == "timeout":
            await asyncio.sleep(0.01)
            raise ProviderTimeoutError("Mock provider timeout")
        if scenario == "rate_limit":
            raise ProviderRateLimitError("Mock provider rate limit")
        if scenario == "provider_error":
            raise ProviderServerError("Mock provider server error")
        if scenario == "cancelled":
            raise UserCancelledError("Mock request cancelled")
