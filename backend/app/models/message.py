from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    sender: Mapped[str] = mapped_column(String)  # CUSTOMER | ASSISTANT | HUMAN
    message: Mapped[str] = mapped_column(String)
    language: Mapped[str] = mapped_column(String, default="English")
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
