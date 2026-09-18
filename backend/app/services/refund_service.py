"""RefundService — mock merchant-refund state + the merchant/customer
status mismatch scenario (spec section 19). Same discipline as
BillService: deterministic insight from already-verified fields, no
invented facts."""

from sqlalchemy.orm import Session

from app.models.refund import Refund
from app.services.audit_service import audit_service
from app.services.case_service import case_service


def _insight(refund: Refund) -> dict:
    has_issue = refund.merchant_status == "COMPLETED" and not refund.customer_received
    message = (
        f"{refund.merchant_name} marked this refund as completed, but it hasn't reached your account yet."
        if has_issue
        else None
    )
    return {"has_issue": has_issue, "message": message}


def _to_dict(refund: Refund) -> dict:
    return {
        "id": refund.id,
        "customer_id": refund.customer_id,
        "merchant_name": refund.merchant_name,
        "amount": refund.amount,
        "original_transaction_id": refund.original_transaction_id,
        "merchant_status": refund.merchant_status,
        "customer_received": refund.customer_received,
        "nishchint_insight": _insight(refund),
    }


class RefundService:
    def get_customer_refunds(self, db: Session, customer_id: str) -> list[dict]:
        rows = db.query(Refund).filter(Refund.customer_id == customer_id).order_by(Refund.created_at.desc()).all()
        return [_to_dict(r) for r in rows]

    def get_refund(self, db: Session, refund_id: str) -> dict | None:
        refund = db.get(Refund, refund_id)
        return _to_dict(refund) if refund else None

    def investigate(self, db: Session, refund_id: str) -> dict:
        refund = db.get(Refund, refund_id)
        if refund is None:
            raise ValueError(f"Refund {refund_id} not found")

        case, created = case_service.get_or_create_case(db, refund.customer_id, None, "REFUND_MISMATCH")
        audit_service.write_event(
            db, event_type="REFUND_CHECKED", actor="AGENT", case_id=case.id, customer_id=refund.customer_id,
            metadata={"refund_id": refund.id, "merchant_name": refund.merchant_name, "insight": _insight(refund)},
        )
        case_service.advance_to(db, case.id, "WAITING_FOR_RESOLUTION", actor="AGENT")
        return {"case_id": case.id, "created": created, "refund": _to_dict(refund)}


refund_service = RefundService()
