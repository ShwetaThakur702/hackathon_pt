from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)  # SYSTEM|AGENT|RULE_ENGINE|N8N|HUMAN|CUSTOMER
    metadata_json: Mapped[str] = mapped_column(String, default="{}")
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
