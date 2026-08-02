from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class LLMRequest:
    provider: str
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 800
    stream: bool = True
    mock_scenario: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    cancellation_event: Any | None = None


@dataclass
class LLMChunk:
    delta: str
    sequence_number: int
    event_type: str = "token"
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    provider_request_id: str | None = None
    latency_ms: int | None = None
    time_to_first_token_ms: int | None = None
    finish_reason: str | None = None
    status: str = "completed"
    safe_metadata: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    provider: str

    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        ...

    async def health_check(self) -> dict[str, Any]:
        ...

    def metadata(self) -> dict[str, Any]:
        ...
