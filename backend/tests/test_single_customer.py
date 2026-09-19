"""Single-customer experience (spec: one signed-in customer, no switcher).

Covers: exactly one seeded customer (Priya/CUST-001), customer-scoped
APIs, numeric UPI Reference IDs as the customer-facing identifier, and
live (never-stale) backend-computed compensation that the API — not the
frontend — is the sole authority for.
"""

from datetime import datetime, timedelta

from app.database.seed import reset_and_seed
from app.models.customer import Customer
from app.services.case_service import case_service
from app.services.followup_service import followup_service
from app.services.simulation_clock import demo_anchor_date, simulation_clock_service


def _at(days_offset: int, hour: int = 9) -> datetime:
    anchor = demo_anchor_date()
    return datetime(anchor.year, anchor.month, anchor.day, hour, 0) + timedelta(days=days_offset)


# --- Single customer -------------------------------------------------------

def test_seed_creates_exactly_one_customer(db_session):
    customers = db_session.query(Customer).all()
    assert len(customers) == 1
    assert customers[0].id == "CUST-001"
    assert customers[0].name == "Priya Sharma"


def test_reset_still_leaves_exactly_one_customer(db_session):
    reset_and_seed(db_session)
    assert db_session.query(Customer).count() == 1
    assert db_session.get(Customer, "CUST-001") is not None


def test_no_other_demo_customer_is_reachable(client):
    for stale_id in ("CUST001", "CUST002", "CUST003"):
        resp = client.get(f"/api/customers/{stale_id}")
        assert resp.status_code == 404


# --- Customer-scoped data ---------------------------------------------------

def test_transactions_are_scoped_to_the_single_customer(client):
    resp = client.get("/api/customers/CUST-001/transactions")
    assert resp.status_code == 200
    txns = resp.json()
    assert len(txns) >= 7
    assert all(t["customer_id"] == "CUST-001" for t in txns)


def test_cases_endpoint_only_ever_returns_priyas_cases(client):
    client.post("/api/bills/BILL-ELEC-001/investigate")
    resp = client.get("/api/cases", params={"customer_id": "CUST-001"})
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) >= 1
    assert all(c["customer_id"] == "CUST-001" for c in cases)


def test_attention_items_are_scoped_to_the_single_customer(client):
    resp = client.get("/api/nishchint/attention", params={"customer_id": "CUST-001"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["items"], list)
    assert len(body["items"]) > 0  # Priya has real deliberate exceptions seeded


def test_notifications_endpoint_is_scoped_to_the_single_customer(client):
    resp = client.get("/api/customers/CUST-001/notifications")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# --- UPI Reference ID --------------------------------------------------------

def test_all_seeded_transactions_have_a_numeric_upi_reference_id(client):
    resp = client.get("/api/customers/CUST-001/transactions")
    txns = resp.json()
    assert len(txns) >= 7
    for t in txns:
        assert t["upi_ref_no"], f"{t['id']} is missing a UPI Reference ID"
        assert t["upi_ref_no"].isdigit(), f"{t['id']}'s UPI Reference ID must be purely numeric"
        assert len(t["upi_ref_no"]) == 12


def test_transaction_detail_endpoint_returns_upi_reference_id(client):
    resp = client.get("/api/transactions/TXN24001")
    assert resp.status_code == 200
    assert resp.json()["upi_ref_no"] == "624718395021"


def test_customer_can_be_identified_by_upi_reference_id_alone(client):
    """The customer should never need to know the internal TXN-xxxx id —
    citing the numeric UPI Reference ID must resolve the same transaction."""
    resp = client.post(
        "/chat",
        json={"customer_id": "CUST-001", "message": "UPI Reference ID 624718395021 payment failed", "case_id": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] is not None
    case = client.get(f"/api/cases/{body['case_id']}").json()
    assert case["transaction"]["id"] == "TXN24001"
    assert case["transaction"]["upi_ref_no"] == "624718395021"


# --- Compensation: backend-authoritative, live, never stale -----------------

def _prep_dispute_case(db_session):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    case_service.transition(db_session, case.id, "INVESTIGATING")
    case_service.transition(db_session, case.id, "DECIDED")
    case_service.transition(db_session, case.id, "ACTION_TAKEN")
    case_service.transition(db_session, case.id, "FOLLOW_UP_SCHEDULED")
    case_service.transition(db_session, case.id, "WAITING_FOR_RESOLUTION")
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))
    return case, followup


def test_compensation_is_zero_before_the_deadline(client, db_session):
    case, _ = _prep_dispute_case(db_session)
    resp = client.get(f"/api/cases/{case.id}")
    body = resp.json()
    assert body["policy_result"]["is_breached"] is False
    assert body["current_compensation"] in (None, 0)


def test_compensation_grows_100_per_day_via_the_api_not_the_frontend(client, db_session):
    case, followup = _prep_dispute_case(db_session)

    simulation_clock_service.advance_to(db_session, _at(6))  # deadline + 1 = 2 days overdue
    followup_service.execute_due_followup(db_session, followup.id)

    body = client.get(f"/api/cases/{case.id}").json()
    assert body["days_overdue"] == 2
    assert body["current_compensation"] == 200
    assert body["policy_result"]["compensation"] == 200  # single authoritative source, not duplicated logic

    from app.models.followup import Followup

    next_followup = (
        db_session.query(Followup).filter(Followup.case_id == case.id, Followup.status == "SCHEDULED").one()
    )
    simulation_clock_service.advance_to(db_session, _at(7))
    followup_service.execute_due_followup(db_session, next_followup.id)

    body = client.get(f"/api/cases/{case.id}").json()
    assert body["days_overdue"] == 3
    assert body["current_compensation"] == 300


def test_compensation_reflects_current_clock_even_without_a_followup_running(client, db_session):
    """The API must compute compensation live from (transaction, demo
    clock) on every read — not only when a scheduled follow-up happens to
    have executed. Advance the clock directly and read the case without
    triggering any follow-up in between."""
    case, followup = _prep_dispute_case(db_session)
    simulation_clock_service.advance_to(db_session, _at(6))
    followup_service.execute_due_followup(db_session, followup.id)

    # Jump the clock further WITHOUT running the next scheduled follow-up.
    simulation_clock_service.advance_to(db_session, _at(9))

    body = client.get(f"/api/cases/{case.id}").json()
    assert body["days_overdue"] == 5
    assert body["current_compensation"] == 500


def test_reset_returns_compensation_state_to_a_clean_slate(client, db_session):
    case, followup = _prep_dispute_case(db_session)
    simulation_clock_service.advance_to(db_session, _at(6))
    followup_service.execute_due_followup(db_session, followup.id)
    assert client.get(f"/api/cases/{case.id}").json()["current_compensation"] == 200

    resp = client.post("/api/simulate/reset")
    assert resp.status_code == 200

    # The old case id no longer exists post-reset (fresh seed).
    assert client.get(f"/api/cases/{case.id}").status_code == 404
    assert client.get("/api/customers/CUST-001").json()["preferred_language"] in ("English", "Hindi", "Hinglish")
