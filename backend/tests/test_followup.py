from datetime import datetime, timedelta

from app.services.case_service import case_service
from app.services.followup_service import followup_service
from app.services.simulation_clock import demo_anchor_date, simulation_clock_service


def _at(days_offset: int, hour: int = 9) -> datetime:
    """A datetime `days_offset` days from the demo anchor ("today") — seed
    data (TXN24001 etc.) is anchored the same way, so this stays correct
    regardless of what day the suite runs on."""
    anchor = demo_anchor_date()
    return datetime(anchor.year, anchor.month, anchor.day, hour, 0) + timedelta(days=days_offset)


def _prep_case(db_session, txn_id="TXN24001", customer_id="CUST001"):
    case, _ = case_service.get_or_create_case(db_session, customer_id, txn_id, "FAILED_PAYMENT")
    case_service.transition(db_session, case.id, "INVESTIGATING")
    case_service.transition(db_session, case.id, "DECIDED")
    case_service.transition(db_session, case.id, "ACTION_TAKEN")
    case_service.transition(db_session, case.id, "FOLLOW_UP_SCHEDULED")
    case_service.transition(db_session, case.id, "WAITING_FOR_RESOLUTION")
    return case


def test_schedule_creates_followup_and_is_idempotent(db_session):
    case = _prep_case(db_session)
    followup1, created1 = followup_service.schedule(db_session, case.id, _at(5))
    followup2, created2 = followup_service.schedule(db_session, case.id, _at(10))
    assert created1 is True
    assert created2 is False
    assert followup1.id == followup2.id


def test_recheck_still_pending_raises_dispute(db_session):
    # TXN24001 (MERCHANT) is seeded with transaction_date = today, so its
    # T+5 deadline is today+5 — breach starts on that day (see PolicyEngine).
    case = _prep_case(db_session)
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))

    simulation_clock_service.advance_to(db_session, _at(6))
    result = followup_service.execute_due_followup(db_session, followup.id)

    assert result["result"] == "DISPUTE_RAISED"
    updated_case = case_service.get_case(db_session, case.id)
    assert updated_case.status == "DISPUTE_RAISED"


def test_recheck_refund_received_resolves_case(db_session):
    from app.models.transaction import Transaction

    case = _prep_case(db_session, txn_id="TXN30001", customer_id="CUST003")
    followup, _ = followup_service.schedule(db_session, case.id, _at(1))

    txn = db_session.get(Transaction, "TXN30001")
    txn.refund_status = "RECEIVED"
    db_session.commit()

    simulation_clock_service.advance_to(db_session, _at(2))
    result = followup_service.execute_due_followup(db_session, followup.id)

    assert result["result"] == "RESOLVED"
    updated_case = case_service.get_case(db_session, case.id)
    assert updated_case.status == "RESOLVED"


def test_dispute_execution_is_idempotent_on_double_execute(db_session):
    case = _prep_case(db_session)
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))
    simulation_clock_service.advance_to(db_session, _at(6))

    followup_service.execute_due_followup(db_session, followup.id)
    second = followup_service.execute_due_followup(db_session, followup.id)

    assert second.get("already_completed") is True

    from app.models.dispute import Dispute

    disputes = db_session.query(Dispute).filter(Dispute.case_id == case.id).all()
    assert len(disputes) == 1


def test_dispute_compensation_grows_on_each_subsequent_daily_recheck(db_session):
    """A dispute isn't a dead end while the refund still hasn't landed —
    each day it's rechecked and still not resolved, the accrued penalty
    must grow (₹100/day here), not freeze at day 1's amount."""
    from app.models.dispute import Dispute
    from app.models.followup import Followup

    case = _prep_case(db_session)
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))

    simulation_clock_service.advance_to(db_session, _at(6))
    first = followup_service.execute_due_followup(db_session, followup.id)
    assert first["result"] == "DISPUTE_RAISED"

    dispute = db_session.query(Dispute).filter(Dispute.case_id == case.id).one()
    assert dispute.compensation_amount == 200  # 2 days overdue (day+5 deadline, checked on day+6) * ₹100/day

    # A fresh followup must have been auto-scheduled to keep the loop alive.
    next_followup = (
        db_session.query(Followup)
        .filter(Followup.case_id == case.id, Followup.status == "SCHEDULED")
        .one()
    )
    assert next_followup.id != followup.id

    simulation_clock_service.advance_to(db_session, _at(7))
    second = followup_service.execute_due_followup(db_session, next_followup.id)
    assert second["result"] == "DISPUTE_RAISED"

    db_session.refresh(dispute)
    assert dispute.compensation_amount == 300  # 3 days overdue now — grew, didn't freeze

    updated_case = case_service.get_case(db_session, case.id)
    assert updated_case.status == "DISPUTE_RAISED"

    # Still exactly one dispute row — growth updates it in place, it never duplicates.
    assert db_session.query(Dispute).filter(Dispute.case_id == case.id).count() == 1


def test_dispute_still_resolves_once_refund_lands_on_a_later_day(db_session):
    from app.models.transaction import Transaction

    case = _prep_case(db_session)
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))

    simulation_clock_service.advance_to(db_session, _at(6))
    followup_service.execute_due_followup(db_session, followup.id)
    assert case_service.get_case(db_session, case.id).status == "DISPUTE_RAISED"

    from app.models.followup import Followup

    next_followup = (
        db_session.query(Followup)
        .filter(Followup.case_id == case.id, Followup.status == "SCHEDULED")
        .one()
    )

    txn = db_session.get(Transaction, "TXN24001")
    txn.refund_status = "RECEIVED"
    db_session.commit()

    simulation_clock_service.advance_to(db_session, _at(7))
    result = followup_service.execute_due_followup(db_session, next_followup.id)

    assert result["result"] == "RESOLVED"
    assert case_service.get_case(db_session, case.id).status == "RESOLVED"
