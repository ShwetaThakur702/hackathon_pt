"""BillService — mock biller-payment state + the provider-acknowledgement
mismatch scenario (spec sections 16, 60). Deliberately lighter than the
core failed-payment flow: T+1/T+5 refund policy doesn't apply to a bill
that our own system shows as PAID, so this does not route through
PolicyEngine — the "insight" here is a direct, deterministic comparison of
two already-verified status fields, computed server-side (never hardcoded
on the frontend).
"""

from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.services.audit_service import audit_service
from app.services.case_service import case_service


def _insight(bill: Bill) -> dict:
    has_issue = bill.status == "PAID" and bill.provider_ack_status == "PENDING"
    message = (
        f"Your payment to {bill.provider_name} was successful, but they haven't acknowledged it yet."
        if has_issue
        else None
    )
    return {"has_issue": has_issue, "message": message}


def _to_dict(bill: Bill) -> dict:
    return {
        "id": bill.id,
        "customer_id": bill.customer_id,
        "category": bill.category,
        "provider_name": bill.provider_name,
        "amount": bill.amount,
        "status": bill.status,
        "provider_ack_status": bill.provider_ack_status,
        "due_date": bill.due_date.isoformat(),
        "paid_date": bill.paid_date.isoformat() if bill.paid_date else None,
        "nishchint_insight": _insight(bill),
    }


class BillService:
    def get_customer_bills(self, db: Session, customer_id: str) -> list[dict]:
        rows = db.query(Bill).filter(Bill.customer_id == customer_id).order_by(Bill.due_date.desc()).all()
        return [_to_dict(b) for b in rows]

    def get_bill(self, db: Session, bill_id: str) -> dict | None:
        bill = db.get(Bill, bill_id)
        return _to_dict(bill) if bill else None

    def investigate(self, db: Session, bill_id: str) -> dict:
        bill = db.get(Bill, bill_id)
        if bill is None:
            raise ValueError(f"Bill {bill_id} not found")

        case, created = case_service.get_or_create_case(db, bill.customer_id, None, "BILL_RECONCILIATION")
        audit_service.write_event(
            db, event_type="BILL_INVESTIGATED", actor="AGENT", case_id=case.id, customer_id=bill.customer_id,
            metadata={"bill_id": bill.id, "provider_name": bill.provider_name, "insight": _insight(bill)},
        )
        # advance_to walks the full forward chain (NEW -> ... -> WAITING_FOR_RESOLUTION)
        # via BFS and is a no-op if the case is already past this point.
        case_service.advance_to(db, case.id, "WAITING_FOR_RESOLUTION", actor="AGENT")
        return {"case_id": case.id, "created": created, "bill": _to_dict(bill)}


bill_service = BillService()
