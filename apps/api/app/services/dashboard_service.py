from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db import models


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        logs = self.db.query(models.InferenceLog).all()
        total = len(logs)
        latencies = sorted([log.latency_ms or 0 for log in logs])
        errors = len([log for log in logs if log.status == "error"])
        cancelled = len([log for log in logs if log.status == "cancelled"])
        successful = len([log for log in logs if log.status == "completed"])
        ttfts = sorted([log.time_to_first_token_ms or 0 for log in logs if log.time_to_first_token_ms is not None])
        retry_count = sum(log.retry_count for log in logs)
        fallback_count = len([log for log in logs if log.fallback_provider])
        return {
            "total_requests": total,
            "average_latency_ms": round(sum(latencies) / total, 2) if total else 0,
            "p50_latency_ms": percentile(latencies, 50),
            "p95_latency_ms": percentile(latencies, 95),
            "error_rate": round(errors / total, 4) if total else 0,
            "cancellation_rate": round(cancelled / total, 4) if total else 0,
            "total_tokens": sum(log.total_tokens for log in logs),
            "estimated_cost": round(sum(log.estimated_total_cost for log in logs), 8),
            "success_rate": round(successful / total, 4) if total else 0,
            "p50_ttft_ms": percentile(ttfts, 50),
            "p95_ttft_ms": percentile(ttfts, 95),
            "input_tokens": sum(log.input_tokens for log in logs),
            "output_tokens": sum(log.output_tokens for log in logs),
            "retry_count": retry_count,
            "fallback_count": fallback_count,
            "replay_count": self.db.query(models.InferenceTrace).filter(models.InferenceTrace.replayed_from_trace_id.is_not(None)).count(),
            "comparison_count": self.db.query(models.ComparisonRun).count(),
            "worker_processing_latency_ms": self._worker_latency(),
            "dead_letter_count": self.db.query(models.DeadLetterEvent).count(),
            "pii_redaction_count": self.db.query(models.PiiRedactionEvent).count(),
        }

    def time_series(self, metric: str) -> list[dict]:
        column = {
            "latency": func.avg(models.InferenceLog.latency_ms),
            "errors": func.sum(case((models.InferenceLog.status == "error", 1), else_=0)),
            "tokens": func.sum(models.InferenceLog.total_tokens),
            "cost": func.sum(models.InferenceLog.estimated_total_cost),
        }.get(metric, func.count(models.InferenceLog.id))
        rows = (
            self.db.query(func.date(models.InferenceLog.created_at).label("bucket"), column.label("value"))
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )
        return [{"bucket": str(bucket), "value": float(value or 0)} for bucket, value in rows]

    def providers(self) -> list[dict]:
        rows = (
            self.db.query(
                models.InferenceLog.provider,
                models.InferenceLog.model,
                func.count(models.InferenceLog.id),
                func.avg(models.InferenceLog.latency_ms),
                func.sum(models.InferenceLog.estimated_total_cost),
            )
            .group_by(models.InferenceLog.provider, models.InferenceLog.model)
            .all()
        )
        return [
            {
                "provider": provider,
                "model": model,
                "label": f"{provider}/{model}",
                "requests": count,
                "average_latency_ms": round(float(latency or 0), 2),
                "estimated_cost": round(float(cost or 0), 8),
            }
            for provider, model, count, latency, cost in rows
        ]

    def _worker_latency(self) -> float:
        rows = self.db.query(models.InferenceSpan.duration_ms).filter(models.InferenceSpan.name == "worker_persisted").all()
        values = [value or 0 for (value,) in rows]
        return round(sum(values) / len(values), 2) if values else 0


def percentile(values: list[int], pct: int) -> float:
    if not values:
        return 0
    index = min(len(values) - 1, round((pct / 100) * (len(values) - 1)))
    return float(values[index])
