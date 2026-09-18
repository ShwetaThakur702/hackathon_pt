from datetime import date, datetime, timezone

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AutoPayMandate(Base):
    """Mock AutoPay mandate (spec section 18). `linked_bill_id` lets
    AutoPayService detect a duplicate-payment risk when the linked bill was
    already paid manually ahead of the mandate's next charge date."""

    __tablename__ = "autopay_mandates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    biller_name: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    frequency: Mapped[str] = mapped_column(String, default="MONTHLY")
    next_charge_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")  # ACTIVE|CANCELLED
    linked_bill_id: Mapped[str | None] = mapped_column(ForeignKey("bills.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
