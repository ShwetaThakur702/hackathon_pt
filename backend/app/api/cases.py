import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.integrations.cognee.cognee_memory_service import cognee_memory_service
from app.integrations.llm.llm_service import llm_service
from app.models.customer import Customer
from app.rules.engine import get_policy_engine
from app.schemas.case import HumanOverrideRequest
from app.services.audit_service import audit_service
from app.services.case_service import InvalidTransitionError, case_service
from app.services.dispute_service import dispute_service
from app.services.followup_service import followup_service
from app.services.memory_service import memory_service
from app.services.notification_service import notification_service
from app.services.simulation_clock import simulation_clock_service
from app.services.transaction_service import transaction_service

router = APIRouter(prefix="/api", tags=["cases"])
policy_engine = get_policy_engine()


def _timeline(db: Session, case_id: str) -> list[dict]:
    events = audit_service.get_case_timeline(db, case_id)
    return [
        {
            "event_type": e.event_type,
            "actor": e.actor,
            "metadata": json.loads(e.metadata_json),
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]


def _case_detail(db: Session, case_id: str) -> dict:
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    customer = db.get(Customer, case.customer_id)
    transaction = transaction_service.get_transaction(db, case.transaction_id) if case.transaction_id else None
    now = simulation_clock_service.now(db)
    policy_result = None
    if transaction:
        # Recomputed fresh on every read from (transaction, current demo-clock
        # time) — never a stored/stale snapshot. This is the ONE authoritative
        # compensation number; Dispute.compensation_amount (below) is kept
        # only as the audit-trail record of what was calculated the last time
        # a follow-up actually ran, not what the UI should display as "now".
        policy_result = policy_engine.evaluate(transaction, now).to_dict()

    followup = followup_service.get_active_followup_for_case(db, case_id)
    dispute = dispute_service.get_existing_dispute_for_case(db, case_id)
    messages = memory_service.get_previous_messages(db, case.customer_id, limit=50)
    messages = [m for m in messages if m["case_id"] == case_id]

    # Cognee is NOT queried here — a real Cognee Cloud /search call can take
    # several seconds, and this endpoint must stay fast since it's the main
    # case-detail page load. Memory is fetched separately and asynchronously
    # by the frontend via GET /api/cases/{case_id}/memory (progressive
    # enhancement — see that endpoint below).
    memory_section: dict = {"cognee_configured": cognee_memory_service.configured, "previous_interactions": [], "related_incidents": []}

    return {
        "id": case.id,
        "status": case.status,
        "priority": case.priority,
        "intent": case.intent,
        "escalation_reason": case.escalation_reason,
        "deadline": case.deadline.isoformat() if case.deadline else None,
        "created_at": case.created_at.isoformat(),
        "customer": {"id": customer.id, "name": customer.name, "preferred_language": customer.preferred_language} if customer else None,
        "transaction": transaction,
        "policy_result": policy_result,
        # Convenience mirrors of policy_result's live numbers, for a UI that
        # just wants "the current number" without reaching into a nested
        # object — always in sync with policy_result since both come from
        # the same evaluate() call above.
        "current_demo_time": now.isoformat(),
        "days_overdue": policy_result["days_overdue"] if policy_result else None,
        "current_compensation": policy_result["compensation"] if policy_result else None,
        "messages": messages,
        "timeline": _timeline(db, case_id),
        "followup": (
            {
                "id": followup.id,
                "status": followup.status,
                "scheduled_for": followup.scheduled_for.isoformat(),
                "attempt_count": followup.attempt_count,
            }
            if followup
            else None
        ),
        "dispute": (
            {"id": dispute.id, "status": dispute.status, "compensation_amount": dispute.compensation_amount}
            if dispute
            else None
        ),
        "memory": memory_section,
    }


@router.get("/cases")
def list_cases(status: str | None = None, priority: str | None = None, customer_id: str | None = None, db: Session = Depends(get_db)):
    cases = case_service.list_cases(db, status=status, priority=priority, customer_id=customer_id)
    now = simulation_clock_service.now(db)
    result = []
    for c in cases:
        transaction = transaction_service.get_transaction(db, c.transaction_id) if c.transaction_id else None
        # Compensation is always recomputed live from the policy engine here
        # too (never a stale stored snapshot) — same authority the case
        # detail page uses, so the list and detail views never disagree.
        policy_result = policy_engine.evaluate(transaction, now).to_dict() if transaction else None
        result.append(
            {
                "id": c.id,
                "customer_id": c.customer_id,
                "transaction_id": c.transaction_id,
                "upi_ref_no": transaction["upi_ref_no"] if transaction else None,
                "merchant_name": transaction["merchant_name"] if transaction else None,
                "amount": transaction["amount"] if transaction else None,
                "intent": c.intent,
                "status": c.status,
                "priority": c.priority,
                "escalation_reason": c.escalation_reason,
                "deadline": policy_result["deadline"] if policy_result else None,
                "days_overdue": policy_result["days_overdue"] if policy_result else None,
                "current_compensation": policy_result["compensation"] if policy_result else None,
                "created_at": c.created_at.isoformat(),
                "closed_at": c.closed_at.isoformat() if c.closed_at else None,
            }
        )
    return result


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    return _case_detail(db, case_id)


@router.get("/cases/{case_id}/memory")
def get_case_memory(case_id: str, db: Session = Depends(get_db)):
    """Separated from GET /cases/{case_id} on purpose: a real Cognee Cloud
    /search call can take several seconds, and the main case page must not
    wait on it. The frontend fetches this after the case itself has
    already rendered."""
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    memory_section: dict = {"cognee_configured": cognee_memory_service.configured, "previous_interactions": [], "related_incidents": []}
    if cognee_memory_service.configured:
        transaction = transaction_service.get_transaction(db, case.transaction_id) if case.transaction_id else None
        merchant_name = transaction.get("merchant_name") if transaction else None

        # Both calls hit Cognee Cloud independently (neither touches `db`)
        # and each can take several seconds — run them in parallel instead
        # of back-to-back so this endpoint isn't ~2x slower than it needs
        # to be. Still fully isolated from GET /cases/{case_id} either way.
        with ThreadPoolExecutor(max_workers=2) as pool:
            case_memory_future = pool.submit(memory_service.retrieve_case_memory, db, case_id)
            incidents_future = pool.submit(memory_service.retrieve_related_incidents, db, merchant_name) if merchant_name else None

            memory_section["previous_interactions"] = [
                {"text": h["text"], "source": "Semantic memory"} for h in case_memory_future.result()
            ]
            if incidents_future is not None:
                memory_section["related_incidents"] = [
                    {"text": h["text"], "source": "Semantic memory"} for h in incidents_future.result()
                ]
    return memory_section


@router.get("/cases/{case_id}/summary")
def get_case_summary(case_id: str, db: Session = Depends(get_db)):
    detail = _case_detail(db, case_id)
    summary = llm_service.summarize_case(
        {"case_id": detail["id"], "status": detail["status"], "escalation_reason": detail["escalation_reason"]}
    )
    return {"case_id": case_id, "summary": summary}


@router.post("/cases/{case_id}/override")
def override_case(case_id: str, payload: HumanOverrideRequest, db: Session = Depends(get_db)):
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    if payload.action == "APPROVE":
        new_status = payload.new_status or "WAITING_FOR_RESOLUTION"
    elif payload.action == "OVERRIDE":
        new_status = payload.new_status
        if not new_status:
            raise HTTPException(status_code=400, detail="new_status is required for OVERRIDE")
    else:
        raise HTTPException(status_code=400, detail="action must be APPROVE or OVERRIDE")

    try:
        case_service.transition(
            db, case_id, new_status, actor="HUMAN",
            metadata={"human_action": payload.action, "operator": payload.operator, "note": payload.note},
        )
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    audit_service.write_event(
        db, event_type="HUMAN_OVERRIDE", actor="HUMAN", case_id=case_id,
        metadata={"action": payload.action, "operator": payload.operator, "note": payload.note},
    )

    # Memory write point (spec section 8): human override.
    transaction = transaction_service.get_transaction(db, case.transaction_id) if case.transaction_id else None
    memory_service.remember_case_event(
        db, case.customer_id, case_id, transaction, event_type="HUMAN_OVERRIDE",
        action=payload.action, new_status=new_status, operator=payload.operator, note=payload.note,
    )

    if payload.note:
        notification_service.notify_customer(db, case.customer_id, case_id, payload.note)

    return _case_detail(db, case_id)
