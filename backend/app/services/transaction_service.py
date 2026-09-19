"""TransactionService — authoritative transaction state + context resolution.

This stands in for the real Paytm transaction API (see spec section 15).
`find_relevant_transaction` implements the context-resolution rules from
spec section 18: never hallucinate a transaction; ask for clarification on
ambiguity instead of guessing.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.transaction import Transaction
from app.services.ids import new_transaction_id, new_upi_ref_no
from app.services.simulation_clock import simulation_clock_service

UNRESOLVED_REFUND_STATUSES = {"PENDING"}

# Deterministic "mock payment gateway" outcome for the hero Send Money demo
# (spec: not random/flaky — the same recipient always reproduces the same
# demo scenario). Real fintech behavior obviously isn't determined by
# recipient name; this stands in for whatever real gateway/bank response
# would have failed in production.
FAILING_MERCHANTS = {"apollo medicals"}


@dataclass
class TransactionMatch:
    status: str  # FOUND | AMBIGUOUS | NOT_FOUND
    transaction: dict | None = None
    candidates: list[dict] = field(default_factory=list)


def _to_dict(txn: Transaction) -> dict:
    return {
        "id": txn.id,
        "upi_ref_no": txn.upi_ref_no,
        "customer_id": txn.customer_id,
        "amount": txn.amount,
        "currency": txn.currency,
        "type": txn.type,
        "merchant_name": txn.merchant_name,
        "status": txn.status,
        "debited": txn.debited,
        "merchant_credited": txn.merchant_credited,
        "refund_status": txn.refund_status,
        "transaction_date": txn.transaction_date.isoformat(),
    }


class TransactionService:
    def get_transaction(self, db: Session, transaction_id: str) -> dict | None:
        txn = db.get(Transaction, transaction_id)
        return _to_dict(txn) if txn else None

    def get_customer_transactions(self, db: Session, customer_id: str, limit: int = 20) -> list[dict]:
        rows = (
            db.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
            .all()
        )
        return [_to_dict(t) for t in rows]

    def _unresolved_failed_transactions(self, db: Session, customer_id: str) -> list[Transaction]:
        return (
            db.query(Transaction)
            .filter(
                Transaction.customer_id == customer_id,
                Transaction.debited.is_(True),
                Transaction.merchant_credited.isnot(True),
                Transaction.refund_status.in_(UNRESOLVED_REFUND_STATUSES),
            )
            .order_by(Transaction.transaction_date.desc())
            .all()
        )

    def find_relevant_transaction(
        self,
        db: Session,
        customer_id: str,
        explicit_transaction_id: str | None = None,
        amount_hint: float | None = None,
        merchant_hint: str | None = None,
    ) -> TransactionMatch:
        if explicit_transaction_id:
            txn = db.get(Transaction, explicit_transaction_id)
            if txn is None:
                # Customers cite the UPI Ref No (12-digit, e.g.
                # "809489842596"), not the internal id — try that too.
                # Normalize away spaces/dashes a customer might type them with.
                normalized = re.sub(r"[^0-9]", "", explicit_transaction_id)
                if normalized:
                    txn = db.query(Transaction).filter(Transaction.upi_ref_no == normalized).first()
            if txn and txn.customer_id == customer_id:
                return TransactionMatch(status="FOUND", transaction=_to_dict(txn))
            return TransactionMatch(status="NOT_FOUND")

        unresolved = self._unresolved_failed_transactions(db, customer_id)

        if amount_hint is not None:
            matches = [t for t in unresolved if abs(t.amount - amount_hint) < 0.01]
            if merchant_hint:
                narrowed = [t for t in matches if t.merchant_name and merchant_hint.lower() in t.merchant_name.lower()]
                if narrowed:
                    matches = narrowed
            if len(matches) == 1:
                return TransactionMatch(status="FOUND", transaction=_to_dict(matches[0]))
            if len(matches) > 1:
                return TransactionMatch(status="AMBIGUOUS", candidates=[_to_dict(t) for t in matches])
            # Customer stated a specific amount and nothing matches it — do
            # not substitute a different transaction; that would be a
            # hallucinated match, not a resolved one.
            return TransactionMatch(status="NOT_FOUND")

        open_cases = (
            db.query(Case)
            .filter(Case.customer_id == customer_id, Case.status != "RESOLVED", Case.transaction_id.isnot(None))
            .order_by(Case.created_at.desc())
            .all()
        )
        if len(open_cases) == 1:
            txn = db.get(Transaction, open_cases[0].transaction_id)
            if txn:
                return TransactionMatch(status="FOUND", transaction=_to_dict(txn))
        elif len(open_cases) > 1:
            case_txn_ids = {c.transaction_id for c in open_cases}
            candidates = [_to_dict(t) for t in unresolved if t.id in case_txn_ids]
            if candidates:
                return TransactionMatch(status="AMBIGUOUS", candidates=candidates)

        if len(unresolved) == 1:
            return TransactionMatch(status="FOUND", transaction=_to_dict(unresolved[0]))
        if len(unresolved) > 1:
            return TransactionMatch(status="AMBIGUOUS", candidates=[_to_dict(t) for t in unresolved])

        return TransactionMatch(status="NOT_FOUND")

    def send_payment(
        self, db: Session, customer_id: str, recipient_name: str, recipient_type: str, amount: float
    ) -> dict:
        """The "Pay" action behind the Send Money hero demo flow — a real
        transaction row is created and persisted here (never faked only in
        React state), with a freshly generated numeric UPI Reference ID,
        exactly like a real payment gateway callback would produce."""
        fails = recipient_name.strip().lower() in FAILING_MERCHANTS
        txn = Transaction(
            id=new_transaction_id(),
            upi_ref_no=new_upi_ref_no(),
            customer_id=customer_id,
            amount=amount,
            currency="INR",
            type="MERCHANT" if recipient_type == "MERCHANT" else "PERSON",
            merchant_name=recipient_name if recipient_type == "MERCHANT" else None,
            status="FAILED" if fails else "SUCCESS",
            debited=True,
            merchant_credited=False if fails else True,
            refund_status="PENDING" if fails else "NOT_APPLICABLE",
            transaction_date=simulation_clock_service.now(db).date(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return _to_dict(txn)


transaction_service = TransactionService()
