"""DisputeService — mock dispute creation against the mock Paytm/NPCI layer.

`raise_dispute` is idempotent on case_id: re-running the same follow-up
workflow twice must not create two disputes (spec section 44).
"""

from sqlalchemy.orm import Session

from app.models.dispute import Dispute
from app.services.audit_service import audit_service
from app.services.ids import new_dispute_id


class DisputeService:
    def get_existing_dispute_for_case(self, db: Session, case_id: str) -> Dispute | None:
        return db.query(Dispute).filter(Dispute.case_id == case_id).first()

    def raise_dispute(
        self,
        db: Session,
        case_id: str,
        transaction_id: str,
        reason: str,
        compensation_amount: float = 0,
    ) -> tuple[Dispute, bool]:
        existing = self.get_existing_dispute_for_case(db, case_id)
        if existing:
            return existing, False

        dispute = Dispute(
            id=new_dispute_id(),
            case_id=case_id,
            transaction_id=transaction_id,
            status="RAISED",
            reason=reason,
            compensation_amount=compensation_amount,
        )
        db.add(dispute)
        db.commit()
        db.refresh(dispute)

        audit_service.write_event(
            db,
            event_type="DISPUTE_RAISED",
            actor="AGENT",
            case_id=case_id,
            metadata={"dispute_id": dispute.id, "reason": reason, "compensation_amount": compensation_amount},
        )
        if compensation_amount:
            audit_service.write_event(
                db,
                event_type="COMPENSATION_CALCULATED",
                actor="RULE_ENGINE",
                case_id=case_id,
                metadata={"compensation_amount": compensation_amount},
            )
        return dispute, True

    def get_dispute(self, db: Session, dispute_id: str) -> Dispute | None:
        return db.get(Dispute, dispute_id)

    def update_compensation(self, db: Session, dispute: Dispute, compensation_amount: float) -> Dispute:
        """Called on every daily recheck of an already-raised dispute
        (followup_service) so the accrued penalty keeps growing for each
        additional overdue day, instead of freezing at whatever it was the
        day the dispute was first raised. No-ops (and writes no audit
        event) if the amount hasn't actually changed since the last check."""
        if compensation_amount == dispute.compensation_amount:
            return dispute

        previous = dispute.compensation_amount
        dispute.compensation_amount = compensation_amount
        db.commit()
        db.refresh(dispute)

        audit_service.write_event(
            db,
            event_type="COMPENSATION_CALCULATED",
            actor="RULE_ENGINE",
            case_id=dispute.case_id,
            metadata={"compensation_amount": compensation_amount, "previous_amount": previous},
        )
        return dispute


dispute_service = DisputeService()
