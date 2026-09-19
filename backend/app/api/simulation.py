"""Demo clock controls (spec sections 21-22, 37).

Advancing the clock past a scheduled follow-up's `scheduled_for` both
notifies n8n (if configured) and directly executes the same deterministic
follow-up logic, so the autonomous loop is fully demonstrable even without a
live n8n Cloud workflow — see FollowupService docstring for why this is not
"faking" the follow-up.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.seed import reset_and_seed
from app.database.session import get_db
from app.services.audit_service import audit_service
from app.services.followup_service import followup_service
from app.services.n8n_client import n8n_client
from app.services.simulation_clock import simulation_clock_service
from app.schemas.simulation import AdvanceTimeRequest

router = APIRouter(prefix="/api/simulate", tags=["simulation"])


def _run_due_followups(db: Session):
    now = simulation_clock_service.now(db)
    due = followup_service.get_due_followups(db, now)
    results = []
    for followup in due:
        n8n_client.trigger_followup_due(
            {"followup_id": followup.id, "case_id": followup.case_id, "action": "RECHECK_FAILED_PAYMENT"}
        )
        results.append(followup_service.execute_due_followup(db, followup.id))
    return results


@router.post("/advance-time")
def advance_time(payload: AdvanceTimeRequest, db: Session = Depends(get_db)):
    new_time = simulation_clock_service.advance(db, days=payload.days, hours=payload.hours)
    audit_service.write_event(db, event_type="SIM_CLOCK_ADVANCED", actor="SYSTEM", metadata={"days": payload.days, "hours": payload.hours})
    executed = _run_due_followups(db)
    return {"current_time": new_time.isoformat(), "followups_executed": executed}


@router.post("/advance-to-deadline")
def advance_to_deadline(case_id: str | None = None, db: Session = Depends(get_db)):
    from app.models.followup import Followup

    # Scoped to the case being viewed when given (case detail page always
    # passes it) — without this, this endpoint picked whichever SCHEDULED
    # followup across ALL cases in the system was earliest, so clicking
    # "Advance to Deadline" on one case's page could jump the clock past a
    # completely different case's deadline while leaving this one still
    # WAITING_FOR_RESOLUTION with its own deadline unexecuted.
    if case_id:
        target_followup = followup_service.get_active_followup_for_case(db, case_id)
    else:
        target_followup = (
            db.query(Followup)
            .filter(Followup.status == "SCHEDULED")
            .order_by(Followup.scheduled_for.asc())
            .first()
        )
    if target_followup is None:
        return {"current_time": simulation_clock_service.now(db).isoformat(), "followups_executed": []}

    new_time = simulation_clock_service.advance_to(db, target_followup.scheduled_for)
    audit_service.write_event(db, event_type="SIM_CLOCK_ADVANCED", actor="SYSTEM", metadata={"target": "next_deadline", "case_id": case_id})
    executed = _run_due_followups(db)
    return {"current_time": new_time.isoformat(), "followups_executed": executed}


@router.get("/current-time")
def current_time(db: Session = Depends(get_db)):
    return {"current_time": simulation_clock_service.now(db).isoformat()}


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    reset_and_seed(db)
    return {"status": "reset", "current_time": simulation_clock_service.now(db).isoformat()}
