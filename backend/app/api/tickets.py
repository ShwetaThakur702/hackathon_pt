from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.case import TicketCreateRequest
from app.services.ticket_service import ticket_service

router = APIRouter(prefix="/api", tags=["tickets"])


@router.post("/tickets")
def create_ticket(payload: TicketCreateRequest, db: Session = Depends(get_db)):
    case, created = ticket_service.create_ticket(db, payload.customer_id, payload.transaction_id, payload.intent)
    return {"ticket_id": case.id, "status": case.status, "created": created}


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    case = ticket_service.get_ticket(db, ticket_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket_id": case.id, "status": case.status, "customer_id": case.customer_id, "transaction_id": case.transaction_id}
