from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.bill_service import bill_service

router = APIRouter(prefix="/api", tags=["bills"])


@router.get("/customers/{customer_id}/bills")
def get_customer_bills(customer_id: str, db: Session = Depends(get_db)):
    return bill_service.get_customer_bills(db, customer_id)


@router.get("/bills/{bill_id}")
def get_bill(bill_id: str, db: Session = Depends(get_db)):
    bill = bill_service.get_bill(db, bill_id)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.post("/bills/{bill_id}/investigate")
def investigate_bill(bill_id: str, db: Session = Depends(get_db)):
    try:
        return bill_service.investigate(db, bill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
