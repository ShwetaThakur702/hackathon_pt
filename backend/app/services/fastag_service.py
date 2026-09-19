"""FastagService — mock FASTag account state + the recharge/balance
mismatch scenario (spec section 17)."""

from sqlalchemy.orm import Session

from app.models.fastag_account import FastagAccount
from app.services.audit_service import audit_service
from app.services.case_service import case_service
from app.services.followup_service import followup_service


def _insight(account: FastagAccount) -> dict:
    has_issue = account.last_recharge_status == "BALANCE_UPDATE_PENDING"
    message = (
        f"Your ₹{account.last_recharge_amount:.0f} recharge was successful, but your FASTag balance hasn't "
        "fully updated yet."
        if has_issue
        else None
    )
    return {"has_issue": has_issue, "message": message}


def _to_dict(account: FastagAccount) -> dict:
    return {
        "id": account.id,
        "customer_id": account.customer_id,
        "balance": account.balance,
        "last_recharge_amount": account.last_recharge_amount,
        "last_recharge_status": account.last_recharge_status,
        "nishchint_insight": _insight(account),
    }


class FastagService:
    def get_account(self, db: Session, customer_id: str) -> dict | None:
        account = db.query(FastagAccount).filter(FastagAccount.customer_id == customer_id).first()
        return _to_dict(account) if account else None

    def investigate(self, db: Session, account_id: str) -> dict:
        account = db.get(FastagAccount, account_id)
        if account is None:
            raise ValueError(f"FASTag account {account_id} not found")

        case, created = case_service.get_or_create_case(db, account.customer_id, None, "FASTAG_BALANCE_MISMATCH")
        audit_service.write_event(
            db, event_type="FASTAG_INVESTIGATED", actor="AGENT", case_id=case.id, customer_id=account.customer_id,
            metadata={"account_id": account.id, "insight": _insight(account)},
        )
        case_service.advance_to(db, case.id, "WAITING_FOR_RESOLUTION", actor="AGENT")
        followup_service.schedule_reconciliation_check(db, case.id)
        return {"case_id": case.id, "created": created, "account": _to_dict(account)}


fastag_service = FastagService()
