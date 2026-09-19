from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.payment import SendPaymentRequest
from app.services.transaction_service import transaction_service

router = APIRouter(prefix="/api", tags=["transactions"])


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    txn = transaction_service.get_transaction(db, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.get("/customers/{customer_id}/transactions")
def get_customer_transactions(customer_id: str, db: Session = Depends(get_db)):
    return transaction_service.get_customer_transactions(db, customer_id)


@router.post("/payments/send")
def send_payment(payload: SendPaymentRequest, db: Session = Depends(get_db)):
    """The Send Money hero demo's "Pay" action — creates a real transaction
    via the mock payment gateway (TransactionService.send_payment), never
    simulated only in frontend state. Deterministic per recipient so the
    demo is reproducible, not flaky."""
    return transaction_service.send_payment(
        db, payload.customer_id, payload.recipient_name, payload.recipient_type, payload.amount
    )
