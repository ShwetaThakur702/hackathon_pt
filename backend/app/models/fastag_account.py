from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class FastagAccount(Base):
    """Mock FASTag account (spec section 17)."""

    __tablename__ = "fastag_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    balance: Mapped[float] = mapped_column(Float, default=0)
    last_recharge_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_recharge_status: Mapped[str] = mapped_column(String, default="NONE")  # NONE|SUCCESS|BALANCE_UPDATE_PENDING
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
