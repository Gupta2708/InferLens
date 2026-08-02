"""Reproducible Mock-provider benchmark; results are emitted, never hard-coded."""
import asyncio
import json
import platform
import statistics
from datetime import datetime, timezone
from time import perf_counter

from app.llm.base import ChatMessage, LLMRequest
from app.llm.gateway import LLMGateway


async def main(requests: int = 50, concurrency: int = 10) -> None:
    gateway = LLMGateway(); semaphore = asyncio.Semaphore(concurrency); latencies = []
    async def run() -> None:
        async with semaphore:
            started = perf_counter(); await gateway.generate(LLMRequest("mock", "mock-fast", [ChatMessage("user", "benchmark")], stream=False)); latencies.append((perf_counter() - started) * 1000)
    started = perf_counter(); await asyncio.gather(*(run() for _ in range(requests))); elapsed = perf_counter() - started
    result = {"date": datetime.now(timezone.utc).isoformat(), "environment": {"platform": platform.platform(), "python": platform.python_version()}, "requests": requests, "concurrency": concurrency, "mock_delay_configuration": "MOCK_CHUNK_DELAY_MS (non-streaming mock-fast has no delay)", "requests_per_second": round(requests / elapsed, 2), "p50_request_latency_ms": round(statistics.median(latencies), 3), "p95_request_latency_ms": round(sorted(latencies)[max(0, int(len(latencies) * .95) - 1)], 3), "known_limitations": "Mock-only benchmark; it excludes network, provider, Redis, and worker contention."}
    print(json.dumps(result, indent=2))


if __name__ == "__main__": asyncio.run(main())
