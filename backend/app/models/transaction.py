from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # The customer/UI-facing reference — a 12-digit numeric string matching
    # the "UPI Ref No" format real UPI apps (incl. Paytm) show, e.g.
    # "809489842596". `id` above stays the internal primary key (used for
    # routing, FKs, and the chat-message transaction-ID regex) and is
    # never customer-facing; upi_ref_no is what the frontend displays.
    upi_ref_no: Mapped[str] = mapped_column(String, default="")
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="INR")
    type: Mapped[str] = mapped_column(String)  # PERSON | MERCHANT
    merchant_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)  # SUCCESS | FAILED | PENDING | REVERSED
    debited: Mapped[bool] = mapped_column(Boolean, default=False)
    merchant_credited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    refund_status: Mapped[str] = mapped_column(String, default="NOT_APPLICABLE")
    transaction_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
