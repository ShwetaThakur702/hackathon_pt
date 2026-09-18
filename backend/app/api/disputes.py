from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.rules.engine import get_policy_engine
from app.schemas.case import DisputeCreateRequest
from app.services.case_service import case_service
from app.services.dispute_service import dispute_service
from app.services.simulation_clock import simulation_clock_service
from app.services.transaction_service import transaction_service

router = APIRouter(prefix="/api", tags=["disputes"])
policy_engine = get_policy_engine()


@router.post("/disputes")
def create_dispute(payload: DisputeCreateRequest, db: Session = Depends(get_db)):
    case = case_service.get_case(db, payload.case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    transaction = transaction_service.get_transaction(db, payload.transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    now = simulation_clock_service.now(db)
    policy_result = policy_engine.evaluate(transaction, now)
    dispute, created = dispute_service.raise_dispute(
        db, payload.case_id, payload.transaction_id, payload.reason, policy_result.compensation or 0
    )
    if created and case.status != "DISPUTE_RAISED":
        case_service.advance_to(db, payload.case_id, "DISPUTE_RAISED", actor="AGENT", metadata={"dispute_id": dispute.id})
    return {"dispute_id": dispute.id, "status": dispute.status, "compensation_amount": dispute.compensation_amount, "created": created}


@router.get("/disputes/{dispute_id}")
def get_dispute(dispute_id: str, db: Session = Depends(get_db)):
    dispute = dispute_service.get_dispute(db, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return {
        "id": dispute.id,
        "case_id": dispute.case_id,
        "transaction_id": dispute.transaction_id,
        "status": dispute.status,
        "reason": dispute.reason,
        "compensation_amount": dispute.compensation_amount,
    }
