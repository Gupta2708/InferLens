import asyncio
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import models
from app.db.session import SessionLocal
from app.llm.base import ChatMessage
from app.llm.cost import estimate_cost
from app.observability.metrics import COMPARISONS
from app.observability.redaction import redact_text
from app.observability.telemetry import span
from app.services.chat_service import ChatService, SYSTEM_PROMPT


class ComparisonService:
    def __init__(self, db: Session): self.db = db

    def create(self, payload) -> dict:
        run = models.ComparisonRun(conversation_id=payload.conversation_id, source_message_id=payload.source_message_id, prompt=payload.prompt, context_mode=payload.context_mode, status="queued")
        self.db.add(run); self.db.commit(); self.db.refresh(run)
        return self.get(run.id)

    @staticmethod
    async def execute(run_id: UUID, targets: list[dict], temperature: float = 0.7, max_tokens: int = 800) -> None:
        semaphore = asyncio.Semaphore(get_settings().comparison_max_concurrency)
        async def one(target: dict) -> None:
            async with semaphore:
                db = SessionLocal()
                try:
                    run = db.query(models.ComparisonRun).filter_by(id=run_id).first()
                    if not run: return
                    started = perf_counter(); messages = [ChatMessage("system", SYSTEM_PROMPT), ChatMessage("user", run.prompt)]
                    with span("comparison.target", {"provider": target["provider"], "model": target["model"]}):
                        trace_id, response, error_category = await ChatService(db).generate_once(messages, target["provider"], target["model"], temperature, max_tokens, comparison_run_id=run.id)
                    latency = max(0, int((perf_counter() - started) * 1000)); input_tokens = response.input_tokens if response else max(1, len(run.prompt.split())); output_tokens = response.output_tokens if response else 0
                    _, _, cost = estimate_cost(target["provider"], target["model"], input_tokens, output_tokens)
                    # Comparison output is a user-requested result, not an operational
                    # log preview. Retain only a bounded, redacted display excerpt.
                    output_preview, _ = redact_text(response.content[:500], "comparison_output") if response else ("", [])
                    db.add(models.ComparisonResult(comparison_run_id=run.id, trace_id=trace_id, provider=target["provider"], model=target["model"], status="error" if error_category else "completed", latency_ms=latency, time_to_first_token_ms=response.time_to_first_token_ms if response else None, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens, estimated_total_cost=cost, output_preview=output_preview, error_type=error_category, error_category=error_category, finish_reason=response.finish_reason if response else None, retry_count=int((response.safe_metadata if response else {}).get("retry_count", 0) or 0), fallback_provider=(response.safe_metadata if response else {}).get("fallback_provider"), completed_at=datetime.now(timezone.utc)))
                    db.commit()
                finally: db.close()
        db = SessionLocal()
        try:
            run = db.query(models.ComparisonRun).filter_by(id=run_id).first()
            if not run: return
            run.status = "running"; db.commit()
        finally: db.close()
        with span("comparison.run", {"target_count": len(targets)}): await asyncio.gather(*(one(target) for target in targets), return_exceptions=True)
        db = SessionLocal()
        try:
            run = db.query(models.ComparisonRun).filter_by(id=run_id).first()
            if run:
                results = db.query(models.ComparisonResult).filter_by(comparison_run_id=run_id).all()
                run.status = "completed" if results and all(row.status == "completed" for row in results) else "partial" if results else "error"
                run.completed_at = datetime.now(timezone.utc); db.commit()
                if COMPARISONS: COMPARISONS.labels(run.status).inc()
        finally: db.close()

    async def retry_failed(self, run_id: UUID) -> dict:
        run = self.db.query(models.ComparisonRun).filter_by(id=run_id).first()
        if not run: raise KeyError("comparison_not_found")
        failed = self.db.query(models.ComparisonResult).filter_by(comparison_run_id=run_id, status="error").all()
        for item in failed: self.db.delete(item)
        self.db.commit()
        asyncio.create_task(self.execute(run.id, [{"provider": item.provider, "model": item.model} for item in failed]))
        return self.get(run_id)

    def get(self, run_id) -> dict:
        run = self.db.query(models.ComparisonRun).filter_by(id=run_id).first()
        if not run: raise KeyError("comparison_not_found")
        results = self.db.query(models.ComparisonResult).filter_by(comparison_run_id=run_id).order_by(models.ComparisonResult.created_at).all()
        return {"id": run.id, "prompt": run.prompt, "context_mode": run.context_mode, "status": run.status, "created_at": run.created_at, "completed_at": run.completed_at, "results": results}
