"""Agent tool layer (spec section 14). Every tool wraps a service call and
returns structured data — the LangGraph nodes call only these, never the ORM
directly (architectural Rule 3).
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.rules.engine import get_policy_engine
from app.services.audit_service import audit_service
from app.services.case_service import case_service
from app.services.context_assembler import context_assembler
from app.services.dispute_service import dispute_service
from app.services.followup_service import followup_service
from app.services.memory_service import memory_service
from app.services.notification_service import notification_service
from app.services.ticket_service import ticket_service
from app.services.transaction_service import transaction_service

policy_engine = get_policy_engine()


def get_customer_context(db: Session, customer_id: str) -> dict:
    return memory_service.get_customer_context(db, customer_id)


def assemble_context(db: Session, customer_id: str, current_message: str, current_case_id: str | None = None) -> dict:
    """DB context + Cognee semantic memory, combined (spec section 11)."""
    return context_assembler.assemble(db, customer_id, current_message, current_case_id)


def find_relevant_transaction(
    db: Session, customer_id: str, transaction_id: str | None, amount: float | None, merchant_hint: str | None
) -> dict:
    match = transaction_service.find_relevant_transaction(
        db, customer_id, explicit_transaction_id=transaction_id, amount_hint=amount, merchant_hint=merchant_hint
    )
    return {"status": match.status, "transaction": match.transaction, "candidates": match.candidates}


def get_transaction(db: Session, transaction_id: str) -> dict | None:
    return transaction_service.get_transaction(db, transaction_id)


def create_ticket(db: Session, customer_id: str, transaction_id: str | None, intent: str) -> dict:
    case, created = ticket_service.create_ticket(db, customer_id, transaction_id, intent)
    return {"case_id": case.id, "created": created, "status": case.status}


def get_case(db: Session, case_id: str) -> dict | None:
    case = case_service.get_case(db, case_id)
    if case is None:
        return None
    return {
        "id": case.id,
        "customer_id": case.customer_id,
        "transaction_id": case.transaction_id,
        "status": case.status,
        "deadline": case.deadline.isoformat() if case.deadline else None,
        "escalation_reason": case.escalation_reason,
    }


def evaluate_policy(transaction: dict, current_time: datetime) -> dict:
    return policy_engine.evaluate(transaction, current_time).to_dict()


def calculate_compensation(transaction: dict, current_time: datetime) -> dict:
    return policy_engine.evaluate(transaction, current_time).to_dict()


def schedule_followup(db: Session, case_id: str, scheduled_for: datetime) -> dict:
    followup, created = followup_service.schedule(db, case_id, scheduled_for)
    return {"followup_id": followup.id, "created": created, "scheduled_for": followup.scheduled_for.isoformat()}


def raise_dispute(db: Session, case_id: str, transaction_id: str, reason: str, compensation_amount: float) -> dict:
    dispute, created = dispute_service.raise_dispute(db, case_id, transaction_id, reason, compensation_amount)
    return {"dispute_id": dispute.id, "created": created, "status": dispute.status}


def escalate_to_human(db: Session, case_id: str, reason: str) -> dict:
    case_service.advance_to(db, case_id, "HUMAN_ESCALATED", actor="AGENT", metadata={"reason": reason})
    case_service.update_fields(db, case_id, escalation_reason=reason, priority="HIGH")
    audit_service.write_event(db, event_type="ESCALATION_CREATED", actor="AGENT", case_id=case_id, metadata={"reason": reason})
    return {"case_id": case_id, "status": "HUMAN_ESCALATED", "reason": reason}


def notify_customer(db: Session, customer_id: str, case_id: str | None, message: str) -> dict:
    notification = notification_service.notify_customer(db, customer_id, case_id, message)
    return {"notification_id": notification.id, "status": notification.status}


def write_audit_event(db: Session, event_type: str, actor: str, case_id: str | None = None, customer_id: str | None = None, metadata: dict | None = None) -> dict:
    entry = audit_service.write_event(db, event_type, actor, case_id=case_id, customer_id=customer_id, metadata=metadata)
    return {"audit_id": entry.id, "event_type": entry.event_type}
