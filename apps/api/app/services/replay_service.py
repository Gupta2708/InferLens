from app.llm.base import ChatMessage
from app.llm.cost import estimate_cost
from app.observability.metrics import REPLAYS
from app.observability.telemetry import span
from app.services.chat_service import ChatService
from time import perf_counter


class ReplayService:
    def __init__(self, db):
        self.db = db

    async def replay(self, trace_id: str, options) -> dict:
        from app.db import models

        log = self.db.query(models.InferenceLog).filter_by(trace_id=trace_id).first()
        if not log:
            raise KeyError("trace_not_found")
        snapshot = dict(log.request_snapshot_json or {})
        messages = snapshot.get("messages", [])
        if not messages and not options.edited_user_message:
            raise ValueError("content_not_captured")
        if options.without_context and messages:
            messages = messages[-1:]
        if options.edited_user_message:
            if messages:
                messages[-1]["content"] = options.edited_user_message
            else:
                messages = [{"role": "user", "content": options.edited_user_message}]
        provider = options.provider or snapshot.get("provider") or log.provider
        model = options.model or snapshot.get("model") or log.model
        temperature = options.temperature if options.temperature is not None else snapshot.get("temperature", 0.7)
        chat_messages = [ChatMessage(m["role"], m["content"]) for m in messages]
        started = perf_counter()
        with span("replay.execute", {"original_trace_id": trace_id, "provider": provider, "model": model}):
            new_trace_id, response, error_type = await ChatService(self.db).generate_once(
                chat_messages, provider, model, temperature, snapshot.get("max_tokens", 800), options.mock_scenario, replayed_from_trace_id=trace_id
            )
        if response:
            response.latency_ms = max(0, int((perf_counter() - started) * 1000))
        _, _, replay_cost = estimate_cost(provider, model, response.input_tokens if response else 0, response.output_tokens if response else 0)
        if REPLAYS:
            REPLAYS.labels("error" if error_type else "completed").inc()
        return {
            "trace_id": new_trace_id,
            "status": "error" if error_type else "completed",
            "output_preview": response.content[:500] if response else "",
            "error_type": error_type,
            "original": {"provider": log.provider, "model": log.model, "status": log.status, "latency_ms": log.latency_ms, "time_to_first_token_ms": log.time_to_first_token_ms, "input_tokens": log.input_tokens, "output_tokens": log.output_tokens, "estimated_cost": log.estimated_total_cost, "finish_reason": log.finish_reason, "output": log.output_preview},
            "replay": {"provider": provider, "model": model, "status": "error" if error_type else "completed", "latency_ms": response.latency_ms if response else None, "time_to_first_token_ms": response.time_to_first_token_ms if response else None, "input_tokens": response.input_tokens if response else 0, "output_tokens": response.output_tokens if response else 0, "estimated_cost": replay_cost, "finish_reason": response.finish_reason if response else None, "output": response.content[:500] if response and self.db else ""},
        }
