import asyncio
import json
import random
import time
from dataclasses import dataclass, field

from app.config import get_settings
from app.llm.errors import NormalizedError


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    def __init__(self) -> None:
        self.states: dict[str, CircuitState] = {}

    def allow(self, provider: str) -> bool:
        state = self.states.get(provider)
        if not state or state.opened_at is None:
            return True
        if time.monotonic() - state.opened_at >= get_settings().circuit_breaker_recovery_seconds:
            state.opened_at = None
            state.failures = 0
            return True
        return False

    def success(self, provider: str) -> None:
        self.states[provider] = CircuitState()

    def failure(self, provider: str, error: NormalizedError) -> str | None:
        if not error.retryable:
            return None
        state = self.states.setdefault(provider, CircuitState())
        state.failures += 1
        if state.failures >= get_settings().circuit_breaker_failure_threshold:
            state.opened_at = time.monotonic()
            return "opened"
        return "failure_recorded"


breaker = CircuitBreaker()


def fallback_chain(provider: str, available_real_providers: set[str] | None = None) -> list[str]:
    try:
        parsed = json.loads(get_settings().provider_fallbacks)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, dict):
        parsed = {}
    # An explicit mapping (including []) overrides the safe reciprocal default.
    if provider in parsed:
        value = parsed[provider]
    elif provider == "openai":
        value = ["gemini"]
    elif provider == "gemini":
        value = ["openai"]
    else:
        value = []
    allowed = available_real_providers or {"openai", "gemini"}
    return [item for item in value if isinstance(item, str) and item != provider and item in allowed and item != "mock"]


async def retry_delay(attempt: int) -> None:
    settings = get_settings()
    base = settings.provider_retry_base_ms / 1000
    # Full jitter prevents retries from synchronizing under provider outages.
    await asyncio.sleep(random.uniform(0, base * (2**attempt)))


@dataclass
class RoutingAttempt:
    provider: str
    attempt: int
    outcome: str
    error_category: str | None = None
    circuit_state: str | None = None


@dataclass
class RoutingResult:
    attempts: list[RoutingAttempt] = field(default_factory=list)

    def metadata(self) -> list[dict]:
        return [attempt.__dict__.copy() for attempt in self.attempts]
