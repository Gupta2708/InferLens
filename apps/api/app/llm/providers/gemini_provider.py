import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings
from app.llm.base import LLMChunk, LLMRequest, LLMResponse
from app.llm.errors import ConnectionError, InvalidRequestError, ProviderAuthError, ProviderModelNotFoundError, ProviderRateLimitError, ProviderServerError, ProviderTimeoutError, StreamInterruptedError


class GeminiProvider:
    provider = "gemini"

    def _url(self, request: LLMRequest, action: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{request.model}:{action}"

    def _payload(self, request: LLMRequest) -> dict:
        system = "\n".join(message.content for message in request.messages if message.role == "system").strip()
        generation_config = {"temperature": request.temperature, "maxOutputTokens": request.max_tokens}
        # For Gemini 2.5 Flash, hidden thinking tokens count against the same
        # maxOutputTokens budget as visible text. Disable it by default so a
        # concise answer does not end after its opening sentence.
        if request.model.startswith("gemini-2.5-"):
            generation_config["thinkingConfig"] = {"thinkingBudget": get_settings().gemini_thinking_budget}
        payload = {"contents": [{"role": "model" if message.role == "assistant" else "user", "parts": [{"text": message.content}]} for message in request.messages if message.role != "system" and message.content.strip()], "generationConfig": generation_config}
        if system: payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    def _params(self) -> dict:
        key = get_settings().gemini_api_key
        if not key: raise ProviderAuthError("Gemini credentials are not configured", provider=self.provider)
        return {"key": key}

    async def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                response = await client.post(self._url(request, "generateContent"), params=self._params(), json=self._payload(request))
        except httpx.TimeoutException as exc: raise ProviderTimeoutError("Gemini timed out", provider=self.provider) from exc
        except httpx.HTTPError as exc: raise ConnectionError("Unable to connect to Gemini", provider=self.provider) from exc
        self._raise_for_status(response)
        data = response.json(); candidates = data.get("candidates", []); usage = data.get("usageMetadata", {})
        content = "".join(part.get("text", "") for candidate in candidates for part in candidate.get("content", {}).get("parts", []))
        return LLMResponse(content=content, provider=self.provider, model=request.model, input_tokens=usage.get("promptTokenCount", 0), output_tokens=usage.get("candidatesTokenCount", 0), total_tokens=usage.get("totalTokenCount", 0), provider_request_id=data.get("responseId"), finish_reason=candidates[0].get("finishReason") if candidates else None, safe_metadata={"model_version": data.get("modelVersion")})

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        sequence = 0
        finish_reason: str | None = None
        usage: dict = {}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(get_settings().provider_timeout_seconds, read=None)) as client:
                async with client.stream("POST", self._url(request, "streamGenerateContent"), params={**self._params(), "alt": "sse"}, json=self._payload(request)) as response:
                    self._raise_for_status(response)
                    async for line in response.aiter_lines():
                        if request.cancellation_event is not None and request.cancellation_event.is_set(): return
                        if not line.startswith("data:"): continue
                        try: data = json.loads(line[5:].strip())
                        except json.JSONDecodeError: continue
                        for candidate in data.get("candidates", []):
                            finish_reason = candidate.get("finishReason") or finish_reason
                            for part in candidate.get("content", {}).get("parts", []):
                                delta = part.get("text", "")
                                if delta:
                                    sequence += 1; yield LLMChunk(delta=delta, sequence_number=sequence)
                        usage = data.get("usageMetadata") or usage
            if finish_reason or usage:
                yield LLMChunk(
                    delta="",
                    sequence_number=sequence,
                    event_type="finish",
                    finish_reason=finish_reason,
                    input_tokens=usage.get("promptTokenCount"),
                    output_tokens=usage.get("candidatesTokenCount"),
                    total_tokens=usage.get("totalTokenCount"),
                )
        except httpx.TimeoutException as exc: raise ProviderTimeoutError("Gemini stream timed out", provider=self.provider) from exc
        except httpx.HTTPError as exc: raise StreamInterruptedError("Gemini stream was interrupted", provider=self.provider) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status in {401, 403}: raise ProviderAuthError("Gemini authentication failed", provider=self.provider, status_code=status)
        if status == 429: raise ProviderRateLimitError("Gemini rate limit exceeded", provider=self.provider, status_code=status)
        if status == 404: raise ProviderModelNotFoundError("Gemini model is unavailable", provider=self.provider, status_code=status)
        if status == 400: raise InvalidRequestError("Gemini rejected the request", provider=self.provider, status_code=status)
        if status >= 500: raise ProviderServerError("Gemini is temporarily unavailable", provider=self.provider, status_code=status)
        if status >= 400: raise InvalidRequestError("Gemini request failed", provider=self.provider, status_code=status)

    async def health_check(self) -> dict:
        return {"status": "configured" if bool(get_settings().gemini_api_key) else "not_configured"}

    def metadata(self) -> dict:
        return {"provider": self.provider, "supports_streaming": True}
