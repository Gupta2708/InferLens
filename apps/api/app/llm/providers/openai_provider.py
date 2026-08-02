import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings
from app.llm.base import LLMChunk, LLMRequest, LLMResponse
from app.llm.errors import ConnectionError, InvalidRequestError, ProviderAuthError, ProviderModelNotFoundError, ProviderRateLimitError, ProviderServerError, ProviderTimeoutError, StreamInterruptedError


class OpenAIProvider:
    provider = "openai"

    def _payload(self, request: LLMRequest, stream: bool = False) -> dict:
        return {"model": request.model, "input": [{"role": message.role, "content": [{"type": "input_text", "text": message.content}]} for message in request.messages], "temperature": request.temperature, "max_output_tokens": request.max_tokens, "stream": stream}

    def _headers(self) -> dict:
        key = get_settings().openai_api_key
        if not key:
            raise ProviderAuthError("OpenAI credentials are not configured", provider=self.provider)
        return {"Authorization": f"Bearer {key}"}

    async def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                response = await client.post("https://api.openai.com/v1/responses", headers=self._headers(), json=self._payload(request))
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("OpenAI timed out", provider=self.provider) from exc
        except httpx.HTTPError as exc:
            raise ConnectionError("Unable to connect to OpenAI", provider=self.provider) from exc
        self._raise_for_status(response)
        data = response.json()
        usage = data.get("usage", {})
        return LLMResponse(content=data.get("output_text") or self._extract_output_text(data), provider=self.provider, model=request.model, input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0), total_tokens=usage.get("total_tokens", 0), provider_request_id=data.get("id"), finish_reason=data.get("status"), safe_metadata={"status": data.get("status")})

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        sequence = 0
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(get_settings().provider_timeout_seconds, read=None)) as client:
                async with client.stream("POST", "https://api.openai.com/v1/responses", headers=self._headers(), json=self._payload(request, True)) as response:
                    self._raise_for_status(response)
                    async for line in response.aiter_lines():
                        if request.cancellation_event is not None and request.cancellation_event.is_set():
                            return
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            return
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if event.get("type") == "response.output_text.delta":
                            delta = event.get("delta", "")
                            if delta:
                                sequence += 1
                                yield LLMChunk(delta=delta, sequence_number=sequence)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("OpenAI stream timed out", provider=self.provider) from exc
        except httpx.HTTPError as exc:
            raise StreamInterruptedError("OpenAI stream was interrupted", provider=self.provider) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status in {401, 403}: raise ProviderAuthError("OpenAI authentication failed", provider=self.provider, status_code=status)
        if status == 429: raise ProviderRateLimitError("OpenAI rate limit exceeded", provider=self.provider, status_code=status)
        if status == 404: raise ProviderModelNotFoundError("OpenAI model is unavailable", provider=self.provider, status_code=status)
        if status == 400: raise InvalidRequestError("OpenAI rejected the request", provider=self.provider, status_code=status)
        if status >= 500: raise ProviderServerError("OpenAI is temporarily unavailable", provider=self.provider, status_code=status)
        if status >= 400: raise InvalidRequestError("OpenAI request failed", provider=self.provider, status_code=status)

    def _extract_output_text(self, data: dict) -> str:
        return "".join(content.get("text", "") for item in data.get("output", []) for content in item.get("content", []) if isinstance(content.get("text"), str))

    async def health_check(self) -> dict:
        return {"status": "configured" if bool(get_settings().openai_api_key) else "not_configured"}

    def metadata(self) -> dict:
        return {"provider": self.provider, "supports_streaming": True}
