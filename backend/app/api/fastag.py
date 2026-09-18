from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.fastag_service import fastag_service

router = APIRouter(prefix="/api", tags=["fastag"])


@router.get("/customers/{customer_id}/fastag")
def get_fastag_account(customer_id: str, db: Session = Depends(get_db)):
    account = fastag_service.get_account(db, customer_id)
    if account is None:
        raise HTTPException(status_code=404, detail="No FASTag account for this customer")
    return account


@router.post("/fastag/{account_id}/investigate")
def investigate_fastag(account_id: str, db: Session = Depends(get_db)):
    try:
        return fastag_service.investigate(db, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
