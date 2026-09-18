"""n8n integration endpoints (spec sections 50/51).

POST /workflows/execute-followup — n8n's wait node calls this once a
scheduled follow-up is due. It runs the real recheck -> policy -> decide ->
act loop server-side (FollowupService.execute_due_followup) and is what the
simulated-clock "advance" endpoint also calls directly when N8N_WEBHOOK_URL
isn't configured, so the same deterministic logic runs either way.

POST /workflows/followup-result — the n8n callback contract for a workflow
variant that computes the outcome itself and reports back. Guarded by a
shared secret so nothing but n8n can mutate case state through it.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.schemas.case import WorkflowResultCallback
from app.services.audit_service import audit_service
from app.services.case_service import InvalidTransitionError, case_service
from app.services.followup_service import followup_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/workflows", tags=["workflows"])
settings = get_settings()

RESULT_TO_STATUS = {
    "RESOLVED": "RESOLVED",
    "DISPUTE_RAISED": "DISPUTE_RAISED",
    "HUMAN_ESCALATED": "HUMAN_ESCALATED",
}


@router.post("/execute-followup")
def execute_followup(payload: dict, db: Session = Depends(get_db)):
    followup_id = payload.get("followup_id")
    if not followup_id:
        raise HTTPException(status_code=400, detail="followup_id is required")
    return followup_service.execute_due_followup(db, followup_id)


@router.post("/followup-result")
def followup_result(payload: WorkflowResultCallback, db: Session = Depends(get_db)):
    if payload.secret != settings.n8n_callback_secret:
        raise HTTPException(status_code=401, detail="Invalid callback secret")

    case = case_service.get_case(db, payload.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    audit_service.write_event(
        db, event_type="N8N_CALLBACK_RECEIVED", actor="N8N", case_id=case.id,
        metadata={"workflow_id": payload.workflow_id, "result": payload.result},
    )

    target_status = RESULT_TO_STATUS.get(payload.result)
    if target_status and case.status != target_status:
        try:
            case_service.transition(db, case.id, target_status, actor="N8N", metadata={"workflow_id": payload.workflow_id})
        except InvalidTransitionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        notification_service.notify_customer(
            db, case.customer_id, case.id, f"Your case {case.id} status is now {target_status}."
        )

    return {"case_id": case.id, "status": case.status}
