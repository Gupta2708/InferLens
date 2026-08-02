from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.traces import TraceOut, TraceReplayRequest
from app.services.replay_service import ReplayService
from app.services.trace_service import TraceService

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("/{trace_id}", response_model=TraceOut)
def get_trace(trace_id: str, db: Session = Depends(get_db)):
    try:
        return TraceService(db).get_trace(trace_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Trace not found")


@router.get("/{trace_id}/spans")
def get_spans(trace_id: str, db: Session = Depends(get_db)):
    return TraceService(db).get_trace(trace_id)["spans"]


@router.get("/{trace_id}/replays")
def get_replays(trace_id: str, db: Session = Depends(get_db)):
    return TraceService(db).get_trace(trace_id)["replays"]


@router.post("/{trace_id}/replay")
async def replay(trace_id: str, payload: TraceReplayRequest, db: Session = Depends(get_db)):
    try:
        return await ReplayService(db).replay(trace_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Trace not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
