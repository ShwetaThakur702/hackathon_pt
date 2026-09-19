"""n8n integration endpoints (spec sections 50/51 and the n8n follow-up
workflow upgrade — see n8n/README.md).

POST /workflows/execute-followup — n8n's "Execute Follow-up" node calls this
once the wait node's next_check_at fires. It runs the real recheck ->
policy -> decide -> act loop server-side (FollowupService.execute_due_followup)
and is what the simulated-clock "advance" endpoint also calls directly when
N8N_WEBHOOK_URL isn't configured, so the same deterministic logic runs
either way. Idempotent per followup_id: a duplicate call (retry, replayed
webhook) never re-raises a dispute, re-notifies, or re-transitions the case
— see FollowupService._outcome_snapshot.

POST /workflows/notify-customer — n8n's explicit "Notify Customer" node.
The message text always comes from what /execute-followup already decided
and sent (see its `notification_message` field) — this call is a real HTTP
round trip to the backend, not a second, independently-generated message,
and NotificationService.notify_customer is itself dedup'd on an exact
(customer_id, case_id, message) match, so replaying it is always safe.

POST /workflows/followup-result — n8n's post-execution report. AUDIT ONLY:
it must never re-drive a case transition or send a notification itself —
all of that already happened inside /execute-followup. Making n8n a second
decision-maker over case state is exactly the anti-pattern this contract
avoids (backend + rules engine remain the only source of financial/business
decisions).
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.schemas.case import NotifyCustomerRequest, WorkflowResultCallback
from app.services.audit_service import audit_service
from app.services.case_service import case_service
from app.services.followup_service import followup_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/workflows", tags=["workflows"])
settings = get_settings()


def _check_secret(body_secret: str | None, authorization: str | None) -> None:
    """Accepts either `Authorization: Bearer <secret>` (preferred — spec
    section 21) or the legacy `secret` JSON body field, for backward
    compatibility with an already-deployed n8n workflow that hasn't been
    re-imported yet. Empty/default secret only ever matches in local dev
    where N8N_CALLBACK_SECRET was left unset — never in a real deployment,
    since the setup script refuses to inline a default secret (see
    scripts/setup_n8n_workflow.py)."""
    header_secret = None
    if authorization and authorization.lower().startswith("bearer "):
        header_secret = authorization[7:]
    if (header_secret or body_secret) != settings.n8n_callback_secret:
        raise HTTPException(status_code=401, detail="Invalid callback secret")


@router.post("/execute-followup")
def execute_followup(payload: dict, db: Session = Depends(get_db)):
    followup_id = payload.get("followup_id") or payload.get("event_id")
    if not followup_id:
        raise HTTPException(status_code=400, detail="followup_id (or event_id) is required")
    return followup_service.execute_due_followup(db, followup_id)


@router.post("/notify-customer")
def notify_customer(payload: NotifyCustomerRequest, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    _check_secret(payload.secret, authorization)
    case = case_service.get_case(db, payload.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    notification = notification_service.notify_customer(db, payload.customer_id, payload.case_id, payload.message)
    return {"notification_id": notification.id, "case_id": payload.case_id, "status": notification.status}


@router.post("/followup-result")
def followup_result(payload: WorkflowResultCallback, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    _check_secret(payload.secret, authorization)

    case = case_service.get_case(db, payload.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    # Audit-only — the case's actual state was already decided and
    # persisted by /execute-followup. This just records that n8n reported
    # having seen that outcome, for the workflow-execution audit trail
    # (spec: FOLLOWUP_EXECUTED / DISPUTE_RAISED / etc already exist from
    # the decision step itself; this adds the n8n-side confirmation).
    audit_service.write_event(
        db, event_type="N8N_CALLBACK_RECEIVED", actor="N8N", case_id=case.id,
        metadata={
            "workflow_id": payload.workflow_id,
            "event_id": payload.event_id,
            "correlation_id": payload.correlation_id,
            "result": payload.result,
            "outcome": payload.outcome,
            "action_taken": payload.action_taken,
            "current_compensation": payload.current_compensation,
            "next_check_at": payload.next_check_at,
        },
    )

    return {"case_id": case.id, "status": case.status, "recorded": True}
