from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

# Explicit case state machine transitions. Enforced in CaseService.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"INVESTIGATING"},
    "INVESTIGATING": {"DECIDED", "HUMAN_ESCALATED"},
    "DECIDED": {"ACTION_TAKEN", "HUMAN_ESCALATED"},
    "ACTION_TAKEN": {"FOLLOW_UP_SCHEDULED", "RESOLVED", "DISPUTE_RAISED", "HUMAN_ESCALATED"},
    "FOLLOW_UP_SCHEDULED": {"WAITING_FOR_RESOLUTION", "HUMAN_ESCALATED"},
    "WAITING_FOR_RESOLUTION": {"RECHECKING", "HUMAN_ESCALATED"},
    "RECHECKING": {"RESOLVED", "DISPUTE_RAISED", "HUMAN_ESCALATED", "WAITING_FOR_RESOLUTION"},
    # A raised dispute isn't a dead end while the refund still hasn't
    # arrived — daily follow-ups keep rechecking it (and the compensation
    # keeps accruing for each additional overdue day) until it resolves.
    "DISPUTE_RAISED": {"RECHECKING", "RESOLVED", "HUMAN_ESCALATED"},
    "HUMAN_ESCALATED": {"RESOLVED", "DISPUTE_RAISED", "WAITING_FOR_RESOLUTION"},
    "RESOLVED": set(),
}


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    intent: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="NEW")
    priority: Mapped[str] = mapped_column(String, default="NORMAL")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
