from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String, default="IN_APP")
    message: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="SENT")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
