from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.case import FollowupCreateRequest
from app.services.followup_service import followup_service

router = APIRouter(prefix="/api", tags=["followups"])


@router.post("/followups")
def create_followup(payload: FollowupCreateRequest, db: Session = Depends(get_db)):
    scheduled_for = datetime.fromisoformat(payload.scheduled_for)
    followup, created = followup_service.schedule(db, payload.case_id, scheduled_for)
    return {"followup_id": followup.id, "status": followup.status, "scheduled_for": followup.scheduled_for.isoformat(), "created": created}


@router.get("/followups/{followup_id}")
def get_followup(followup_id: str, db: Session = Depends(get_db)):
    followup = followup_service.get_followup(db, followup_id)
    if followup is None:
        raise HTTPException(status_code=404, detail="Followup not found")
    return {
        "id": followup.id,
        "case_id": followup.case_id,
        "status": followup.status,
        "scheduled_for": followup.scheduled_for.isoformat(),
        "attempt_count": followup.attempt_count,
        "last_run_at": followup.last_run_at.isoformat() if followup.last_run_at else None,
    }
