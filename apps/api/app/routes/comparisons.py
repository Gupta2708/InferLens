from uuid import UUID

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.comparisons import ComparisonCreate, ComparisonRunOut
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])


@router.post("", response_model=ComparisonRunOut)
async def create_comparison(payload: ComparisonCreate, db: Session = Depends(get_db)):
    result = ComparisonService(db).create(payload)
    asyncio.create_task(ComparisonService.execute(result["id"], [target.model_dump() for target in payload.targets], payload.temperature, payload.max_tokens))
    return result


@router.get("/{comparison_run_id}", response_model=ComparisonRunOut)
def get_comparison(comparison_run_id: UUID, db: Session = Depends(get_db)):
    try:
        return ComparisonService(db).get(comparison_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Comparison not found")


@router.post("/{comparison_run_id}/retry-failed", response_model=ComparisonRunOut)
async def retry_failed(comparison_run_id: UUID, db: Session = Depends(get_db)):
    try:
        return await ComparisonService(db).retry_failed(comparison_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Comparison not found")
