from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
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
