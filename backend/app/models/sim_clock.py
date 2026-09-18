from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SimClock(Base):
    """Singleton row (id=1) holding the application's simulated 'now'.

    Real wall-clock time is never used for policy math in simulation mode —
    see SimulationClockService.
    """

    __tablename__ = "sim_clock"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    current_time: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
