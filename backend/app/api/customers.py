from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.customer import UpdateLanguageRequest
from app.services.audit_service import audit_service
from app.services.memory_service import memory_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "preferred_language": customer.preferred_language,
    }


@router.put("/{customer_id}/language")
def update_customer_language(customer_id: str, payload: UpdateLanguageRequest, db: Session = Depends(get_db)):
    """Single source of truth for the customer's response language (spec:
    picked once on the landing page, then every LLM-generated response —
    /chat, the floating assistant, follow-up notifications — must stay
    consistent with it). Persisting it here means every call site that
    already reads `customer.preferred_language` (generate_response,
    FollowupService's notification text, ...) picks it up automatically,
    with no separate per-request language plumbing needed."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    previous = customer.preferred_language
    customer.preferred_language = payload.preferred_language
    db.commit()
    audit_service.write_event(
        db, event_type="LANGUAGE_PREFERENCE_CHANGED", actor="CUSTOMER", customer_id=customer_id,
        metadata={"from": previous, "to": payload.preferred_language},
    )
    return {"id": customer.id, "preferred_language": customer.preferred_language}


@router.get("/{customer_id}/context")
def get_customer_context(customer_id: str, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return memory_service.get_customer_context(db, customer_id)


@router.get("/{customer_id}/notifications")
def get_customer_notifications(customer_id: str, db: Session = Depends(get_db)):
    rows = notification_service.get_customer_notifications(db, customer_id)
    return [
        {"id": n.id, "case_id": n.case_id, "message": n.message, "channel": n.channel, "created_at": n.created_at.isoformat()}
        for n in rows
    ]
