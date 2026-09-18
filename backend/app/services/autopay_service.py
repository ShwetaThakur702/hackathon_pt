"""AutoPayService — mock AutoPay mandates + the manual-payment-vs-mandate
duplicate-risk scenario (spec section 18). Cancelling a mandate mutates
mock state and writes an audit event; it never claims to touch a real bank
mandate (spec section 18's explicit constraint)."""

from sqlalchemy.orm import Session

from app.models.autopay_mandate import AutoPayMandate
from app.models.bill import Bill
from app.services.audit_service import audit_service


def _insight(db: Session, mandate: AutoPayMandate) -> dict:
    if mandate.status != "ACTIVE" or not mandate.linked_bill_id:
        return {"has_issue": False, "message": None}
    linked_bill = db.get(Bill, mandate.linked_bill_id)
    duplicate_risk = bool(
        linked_bill and linked_bill.status == "PAID" and linked_bill.paid_date and linked_bill.paid_date < mandate.next_charge_date
    )
    message = (
        f"You've already paid {mandate.biller_name} manually, but AutoPay is still scheduled to charge "
        f"₹{mandate.amount:.0f} on {mandate.next_charge_date.isoformat()}."
        if duplicate_risk
        else None
    )
    return {"has_issue": duplicate_risk, "message": message}


def _to_dict(db: Session, mandate: AutoPayMandate) -> dict:
    return {
        "id": mandate.id,
        "customer_id": mandate.customer_id,
        "biller_name": mandate.biller_name,
        "amount": mandate.amount,
        "frequency": mandate.frequency,
        "next_charge_date": mandate.next_charge_date.isoformat(),
        "status": mandate.status,
        "nishchint_insight": _insight(db, mandate),
    }


class AutoPayService:
    def get_customer_mandates(self, db: Session, customer_id: str) -> list[dict]:
        rows = db.query(AutoPayMandate).filter(AutoPayMandate.customer_id == customer_id).order_by(AutoPayMandate.next_charge_date.asc()).all()
        return [_to_dict(db, m) for m in rows]

    def get_mandate(self, db: Session, mandate_id: str) -> dict | None:
        mandate = db.get(AutoPayMandate, mandate_id)
        return _to_dict(db, mandate) if mandate else None

    def review(self, db: Session, mandate_id: str) -> dict:
        mandate = db.get(AutoPayMandate, mandate_id)
        if mandate is None:
            raise ValueError(f"Mandate {mandate_id} not found")
        insight = _insight(db, mandate)
        audit_service.write_event(
            db, event_type="AUTOPAY_REVIEWED", actor="AGENT", customer_id=mandate.customer_id,
            metadata={"mandate_id": mandate.id, "insight": insight},
        )
        return {"mandate": _to_dict(db, mandate), "insight": insight}

    def cancel(self, db: Session, mandate_id: str) -> dict:
        mandate = db.get(AutoPayMandate, mandate_id)
        if mandate is None:
            raise ValueError(f"Mandate {mandate_id} not found")
        mandate.status = "CANCELLED"
        db.commit()
        db.refresh(mandate)
        audit_service.write_event(
            db, event_type="AUTOPAY_CANCELLED", actor="AGENT", customer_id=mandate.customer_id,
            metadata={"mandate_id": mandate.id, "biller_name": mandate.biller_name},
        )
        return _to_dict(db, mandate)


autopay_service = AutoPayService()
