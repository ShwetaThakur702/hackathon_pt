from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Refund(Base):
    """Mock refund record (spec section 19) — independent of the UPI
    failed-payment dispute flow. Models a mismatch between what the
    merchant claims (`merchant_status`) and what the customer has actually
    received (`customer_received`)."""

    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    merchant_name: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    original_transaction_id: Mapped[str | None] = mapped_column(String, nullable=True)
    merchant_status: Mapped[str] = mapped_column(String, default="PENDING")  # PENDING|COMPLETED
    customer_received: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
