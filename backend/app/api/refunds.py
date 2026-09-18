from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.refund_service import refund_service

router = APIRouter(prefix="/api", tags=["refunds"])


@router.get("/customers/{customer_id}/refunds")
def get_customer_refunds(customer_id: str, db: Session = Depends(get_db)):
    return refund_service.get_customer_refunds(db, customer_id)


@router.get("/refunds/{refund_id}")
def get_refund(refund_id: str, db: Session = Depends(get_db)):
    refund = refund_service.get_refund(db, refund_id)
    if refund is None:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund


@router.post("/refunds/{refund_id}/investigate")
def investigate_refund(refund_id: str, db: Session = Depends(get_db)):
    try:
        return refund_service.investigate(db, refund_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
