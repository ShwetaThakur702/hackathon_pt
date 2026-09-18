from datetime import date, datetime, timezone

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Bill(Base):
    """Mock biller-payment record (spec section 16). `provider_ack_status`
    modeling the real-world case where our own payment succeeded but the
    biller's system hasn't reflected it yet — the "provider mismatch" demo
    scenario, independent of the UPI-failed-payment policy domain."""

    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    category: Mapped[str] = mapped_column(String)  # ELECTRICITY|WATER|GAS|MOBILE|DTH|BROADBAND|INSURANCE|LOAN|OTHER
    provider_name: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="PENDING")  # PAID|PENDING|FAILED
    provider_ack_status: Mapped[str] = mapped_column(String, default="NOT_APPLICABLE")  # ACKNOWLEDGED|PENDING|NOT_APPLICABLE
    due_date: Mapped[date] = mapped_column(Date)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
