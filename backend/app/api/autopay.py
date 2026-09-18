from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.autopay_service import autopay_service

router = APIRouter(prefix="/api", tags=["autopay"])


@router.get("/customers/{customer_id}/autopay")
def get_customer_mandates(customer_id: str, db: Session = Depends(get_db)):
    return autopay_service.get_customer_mandates(db, customer_id)


@router.post("/autopay/{mandate_id}/review")
def review_mandate(mandate_id: str, db: Session = Depends(get_db)):
    try:
        return autopay_service.review(db, mandate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/autopay/{mandate_id}/cancel")
def cancel_mandate(mandate_id: str, db: Session = Depends(get_db)):
    try:
        return autopay_service.cancel(db, mandate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
