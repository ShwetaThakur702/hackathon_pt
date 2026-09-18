"""SimulationClockService — the application's single source of 'now'.

Real wall-clock time is never used for policy calculations while
SIMULATION_MODE is on. All demo controls (advance day / reset) mutate the
one `sim_clock` row; every other service reads through this service instead
of calling datetime.now() directly.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.sim_clock import SimClock

settings = get_settings()

# This is a Paytm-style, India-focused product — "today" for the demo
# means today in India, not in UTC. Matters near midnight IST (UTC+5:30):
# e.g. 00:30 IST on the 19th is still 19:00 UTC on the 18th, and the demo
# should already show the 19th.
IST = ZoneInfo("Asia/Kolkata")


def demo_anchor_date() -> date:
    """The calendar date the demo is anchored to — always the real
    "today" in India, so seed data and the simulated clock never go stale
    as time passes. Computed fresh (not a module-level constant) so a
    long-running process picks up a new day naturally on the next reset.
    Seed data (app/database/seed.py) builds every date as an offset from
    this same anchor, so relative relationships (T+5 deadlines, "paid
    before the AutoPay mandate" etc.) stay correct no matter what day it's
    reset on."""
    return datetime.now(IST).date()


def demo_start() -> datetime:
    anchor = demo_anchor_date()
    # Stored/compared as UTC internally (consistent with the rest of the
    # app), but the calendar date itself is IST's.
    return datetime(anchor.year, anchor.month, anchor.day, 14, 14, tzinfo=timezone.utc)


class SimulationClockService:
    def _get_row(self, db: Session) -> SimClock:
        row = db.get(SimClock, 1)
        if row is None:
            row = SimClock(id=1, current_time=demo_start())
            db.add(row)
            db.commit()
            db.refresh(row)
        return row

    def now(self, db: Session) -> datetime:
        if not settings.simulation_mode:
            return datetime.now(timezone.utc)
        return self._get_row(db).current_time

    def advance(self, db: Session, days: int = 0, hours: int = 0) -> datetime:
        row = self._get_row(db)
        row.current_time = row.current_time + timedelta(days=days, hours=hours)
        db.commit()
        db.refresh(row)
        return row.current_time

    def advance_to(self, db: Session, target: datetime) -> datetime:
        row = self._get_row(db)
        row.current_time = target
        db.commit()
        db.refresh(row)
        return row.current_time

    def reset(self, db: Session) -> datetime:
        row = self._get_row(db)
        row.current_time = demo_start()
        db.commit()
        db.refresh(row)
        return row.current_time


simulation_clock_service = SimulationClockService()
