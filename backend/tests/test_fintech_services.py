"""Tests for the Bills/FASTag/AutoPay/Refunds/Attention services added for
the fintech-platform product expansion. All exercise real DB state and the
existing case machinery — nothing here is UI-only or hardcoded."""

from app.services.attention_service import get_attention_items
from app.services.autopay_service import autopay_service
from app.services.bill_service import bill_service
from app.services.fastag_service import fastag_service
from app.services.refund_service import refund_service


def test_bill_insight_flags_provider_mismatch(db_session):
    bills = bill_service.get_customer_bills(db_session, "CUST-001")
    elec = next(b for b in bills if b["id"] == "BILL-ELEC-001")
    assert elec["nishchint_insight"]["has_issue"] is True

    normal = next(b for b in bills if b["id"] == "BILL-MOBILE-001")
    assert normal["nishchint_insight"]["has_issue"] is False


def test_bill_investigate_creates_real_case(db_session):
    result = bill_service.investigate(db_session, "BILL-ELEC-001")
    assert result["created"] is True

    from app.services.case_service import case_service
    case = case_service.get_case(db_session, result["case_id"])
    assert case is not None
    assert case.intent == "BILL_RECONCILIATION"
    assert case.status == "WAITING_FOR_RESOLUTION"

    # Idempotent: investigating again reuses the same case.
    second = bill_service.investigate(db_session, "BILL-ELEC-001")
    assert second["case_id"] == result["case_id"]
    assert second["created"] is False


def test_fastag_insight_flags_pending_balance_update(db_session):
    account = fastag_service.get_account(db_session, "CUST-001")
    assert account["nishchint_insight"]["has_issue"] is True
    assert "1000" in account["nishchint_insight"]["message"]


def test_autopay_flags_duplicate_risk_and_cancel_resolves_it(db_session):
    mandates = autopay_service.get_customer_mandates(db_session, "CUST-001")
    cc_mandate = next(m for m in mandates if m["id"] == "AUTOPAY-CC-001")
    assert cc_mandate["nishchint_insight"]["has_issue"] is True

    elec_mandate = next(m for m in mandates if m["id"] == "AUTOPAY-ELEC-001")
    assert elec_mandate["nishchint_insight"]["has_issue"] is False

    cancelled = autopay_service.cancel(db_session, "AUTOPAY-CC-001")
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["nishchint_insight"]["has_issue"] is False


def test_refund_insight_flags_merchant_customer_mismatch(db_session):
    refunds = refund_service.get_customer_refunds(db_session, "CUST-001")
    assert len(refunds) == 1
    assert refunds[0]["nishchint_insight"]["has_issue"] is True


def test_attention_items_aggregate_across_domains(db_session):
    items = get_attention_items(db_session, "CUST-001")
    types = {item["type"] for item in items}
    # TRANSACTION: TXN24001 (Apollo Medicals) and TXN85001 (high-value demo)
    # are both failed/debited/unresolved with no case yet — Nishchint
    # surfaces those proactively too, not just the Bill/FASTag/AutoPay/
    # Refund domain exceptions.
    assert types == {"TRANSACTION", "BILL", "FASTAG", "AUTOPAY", "REFUND"}


def test_attention_shrinks_after_resolving_autopay_conflict(db_session):
    before = len(get_attention_items(db_session, "CUST-001"))
    autopay_service.cancel(db_session, "AUTOPAY-CC-001")
    after = len(get_attention_items(db_session, "CUST-001"))
    assert after == before - 1


def test_customer_with_no_exceptions_has_no_attention_items(db_session):
    # A customer with no bills/fastag/autopay/refunds seeded and no open
    # case must show no attention items — inserted ad hoc since the demo
    # seed now ships exactly one customer (Priya, CUST-001).
    from app.models.customer import Customer

    db_session.add(Customer(id="CUST-EMPTY", name="No Exceptions Customer"))
    db_session.commit()

    items = get_attention_items(db_session, "CUST-EMPTY")
    assert items == []


def test_cases_list_filters_by_customer(client):
    client.post("/api/bills/BILL-ELEC-001/investigate")
    resp = client.get("/api/cases", params={"customer_id": "CUST-001"})
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) >= 1
    assert all(c["customer_id"] == "CUST-001" for c in cases)


def test_attention_endpoint_reflects_seeded_exceptions(client):
    resp = client.get("/api/nishchint/attention", params={"customer_id": "CUST-001"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_attention"] is True
    # Bill, FASTag, AutoPay, Refund exceptions (4) + 2 unresolved failed
    # transactions with no case yet (TXN24001, TXN85001).
    assert len(body["items"]) == 6


def test_bills_and_refund_endpoints(client):
    assert client.get("/api/customers/CUST-001/bills").status_code == 200
    assert client.get("/api/customers/CUST-001/fastag").status_code == 200
    assert client.get("/api/customers/CUST-001/autopay").status_code == 200
    refunds = client.get("/api/customers/CUST-001/refunds").json()
    assert len(refunds) == 1
    detail = client.get(f"/api/refunds/{refunds[0]['id']}")
    assert detail.status_code == 200


def test_notifications_are_seeded_not_empty_on_a_fresh_demo(client):
    resp = client.get("/api/customers/CUST-001/notifications")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 3
    assert all(item["message"] for item in items)
    # Newest first.
    timestamps = [item["created_at"] for item in items]
    assert timestamps == sorted(timestamps, reverse=True)
