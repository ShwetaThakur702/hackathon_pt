"""n8n integration endpoints: /execute-followup (enriched contract +
idempotent replay), /notify-customer (real, dedup'd), /followup-result
(audit-only — must never re-drive case state itself)."""

from datetime import datetime, timedelta

from app.config import get_settings
from app.models.notification import Notification
from app.services.case_service import case_service
from app.services.followup_service import followup_service
from app.services.simulation_clock import demo_anchor_date, simulation_clock_service

settings = get_settings()


def _at(days_offset: int, hour: int = 9) -> datetime:
    anchor = demo_anchor_date()
    return datetime(anchor.year, anchor.month, anchor.day, hour, 0) + timedelta(days=days_offset)


def _prep_dispute_case(db_session):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    case_service.transition(db_session, case.id, "INVESTIGATING")
    case_service.transition(db_session, case.id, "DECIDED")
    case_service.transition(db_session, case.id, "ACTION_TAKEN")
    case_service.transition(db_session, case.id, "FOLLOW_UP_SCHEDULED")
    case_service.transition(db_session, case.id, "WAITING_FOR_RESOLUTION")
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))
    return case, followup


def test_execute_followup_returns_the_enriched_outcome_contract(client, db_session):
    case, followup = _prep_dispute_case(db_session)
    simulation_clock_service.advance_to(db_session, _at(6))

    resp = client.post("/api/workflows/execute-followup", json={"followup_id": followup.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "UNRESOLVED"
    assert body["outcome"] == "DISPUTE_RAISED"
    assert body["action_taken"] == "raise_dispute"
    assert body["current_compensation"] == 200  # backend-calculated, not n8n
    assert body["next_check_at"] is not None
    assert body["notification_message"]


def test_execute_followup_accepts_event_id_alias(client, db_session):
    _, followup = _prep_dispute_case(db_session)
    simulation_clock_service.advance_to(db_session, _at(6))
    resp = client.post("/api/workflows/execute-followup", json={"event_id": followup.id})
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "DISPUTE_RAISED"


def test_execute_followup_is_idempotent_on_replay_no_duplicate_dispute(client, db_session):
    from app.models.dispute import Dispute

    case, followup = _prep_dispute_case(db_session)
    simulation_clock_service.advance_to(db_session, _at(6))

    first = client.post("/api/workflows/execute-followup", json={"followup_id": followup.id}).json()
    second = client.post("/api/workflows/execute-followup", json={"followup_id": followup.id}).json()

    assert second["already_completed"] is True
    # The replay still returns a coherent, branchable contract, not just a bare flag.
    assert second["outcome"] == "DISPUTE_RAISED"
    assert second["current_compensation"] == first["current_compensation"]

    disputes = db_session.query(Dispute).filter(Dispute.case_id == case.id).all()
    assert len(disputes) == 1


def test_notify_customer_sends_a_real_notification(client, db_session):
    case, _ = _prep_dispute_case(db_session)
    resp = client.post(
        "/api/workflows/notify-customer",
        json={"case_id": case.id, "customer_id": "CUST-001", "message": "Your dispute has been raised.", "secret": settings.n8n_callback_secret},
    )
    assert resp.status_code == 200
    assert db_session.query(Notification).filter(Notification.case_id == case.id).count() == 1


def test_notify_customer_is_idempotent_on_the_exact_same_message(client, db_session):
    case, _ = _prep_dispute_case(db_session)
    payload = {"case_id": case.id, "customer_id": "CUST-001", "message": "Your dispute has been raised.", "secret": settings.n8n_callback_secret}
    client.post("/api/workflows/notify-customer", json=payload)
    client.post("/api/workflows/notify-customer", json=payload)
    assert db_session.query(Notification).filter(Notification.case_id == case.id).count() == 1


def test_notify_customer_accepts_authorization_bearer_header(client, db_session):
    case, _ = _prep_dispute_case(db_session)
    resp = client.post(
        "/api/workflows/notify-customer",
        json={"case_id": case.id, "customer_id": "CUST-001", "message": "Header-authed message."},
        headers={"Authorization": f"Bearer {settings.n8n_callback_secret}"},
    )
    assert resp.status_code == 200


def test_notify_customer_rejects_wrong_secret(client, db_session):
    case, _ = _prep_dispute_case(db_session)
    resp = client.post(
        "/api/workflows/notify-customer",
        json={"case_id": case.id, "customer_id": "CUST-001", "message": "hi", "secret": "wrong"},
    )
    assert resp.status_code == 401


def test_followup_result_is_audit_only_and_never_transitions_the_case(client, db_session):
    """The old design let n8n's report drive a case transition itself —
    that made n8n a second decision-maker. It must now be a pure audit
    record: reporting RESOLVED for a case that's actually still
    DISPUTE_RAISED must NOT flip the case to RESOLVED."""
    case, followup = _prep_dispute_case(db_session)
    simulation_clock_service.advance_to(db_session, _at(6))
    client.post("/api/workflows/execute-followup", json={"followup_id": followup.id})

    updated = case_service.get_case(db_session, case.id)
    assert updated.status == "DISPUTE_RAISED"

    resp = client.post(
        "/api/workflows/followup-result",
        json={"case_id": case.id, "result": "RESOLVED", "outcome": "RESOLVED", "secret": settings.n8n_callback_secret},
    )
    assert resp.status_code == 200
    assert resp.json()["recorded"] is True

    db_session.expire_all()
    still = case_service.get_case(db_session, case.id)
    assert still.status == "DISPUTE_RAISED"  # unchanged — n8n's report never drove this


def test_followup_result_rejects_wrong_secret(client, db_session):
    case, _ = _prep_dispute_case(db_session)
    resp = client.post(
        "/api/workflows/followup-result",
        json={"case_id": case.id, "result": "DISPUTE_RAISED", "secret": "wrong"},
    )
    assert resp.status_code == 401
