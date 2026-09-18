"""Proactive-attention endpoint (spec section 30) — what the home dashboard
and the contextual assistant launcher surface to the customer. Computed
fresh from current state every call; see AttentionService."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.attention_service import get_attention_items

router = APIRouter(prefix="/api/nishchint", tags=["nishchint"])


@router.get("/attention")
def attention(customer_id: str, db: Session = Depends(get_db)):
    items = get_attention_items(db, customer_id)
    return {"has_attention": len(items) > 0, "items": items}
