"""TicketService — thin wrapper the agent calls to open a support ticket.

In this prototype a "ticket" and a "case" are the same underlying record
(spec doesn't define a separate tickets table); this service exists so the
agent's tool surface matches spec section 14 (`create_ticket`) and so a
future split into a distinct ticketing system stays a one-file change.
"""

from sqlalchemy.orm import Session

from app.models.case import Case
from app.services.audit_service import audit_service
from app.services.case_service import case_service


class TicketService:
    def create_ticket(self, db: Session, customer_id: str, transaction_id: str | None, intent: str) -> tuple[Case, bool]:
        case, created = case_service.get_or_create_case(db, customer_id, transaction_id, intent)
        audit_service.write_event(
            db,
            event_type="TICKET_CREATED",
            actor="AGENT",
            case_id=case.id,
            customer_id=customer_id,
            metadata={"reused_existing": not created},
        )
        return case, created

    def get_ticket(self, db: Session, case_id: str) -> Case | None:
        return case_service.get_case(db, case_id)


ticket_service = TicketService()
