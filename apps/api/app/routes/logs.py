from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.logs import LogDetailOut, LogOut

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=list[LogOut])
def list_logs(
    provider: str | None = None,
    model: str | None = None,
    status: str | None = None,
    conversation_id: str | None = None,
    trace_id: str | None = None,
    error_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    latency_gt: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.InferenceLog)
    if provider:
        query = query.filter(models.InferenceLog.provider == provider)
    if model:
        query = query.filter(models.InferenceLog.model == model)
    if status:
        query = query.filter(models.InferenceLog.status == status)
    if conversation_id:
        query = query.filter(models.InferenceLog.conversation_id == conversation_id)
    if trace_id:
        query = query.filter(models.InferenceLog.trace_id == trace_id)
    if error_type:
        query = query.filter(models.InferenceLog.error_type == error_type)
    if date_from:
        query = query.filter(models.InferenceLog.created_at >= date_from)
    if date_to:
        query = query.filter(models.InferenceLog.created_at <= date_to)
    if latency_gt is not None:
        query = query.filter(models.InferenceLog.latency_ms > latency_gt)
    return query.order_by(models.InferenceLog.created_at.desc()).limit(200).all()


@router.get("/{trace_id}", response_model=LogDetailOut)
def get_log(trace_id: str, db: Session = Depends(get_db)):
    log = db.query(models.InferenceLog).filter_by(trace_id=trace_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log
