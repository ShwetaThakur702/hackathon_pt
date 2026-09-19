"""GET /api/cases/{id} must never block on Cognee (a real Cloud /search
call can take several seconds); semantic memory is a separate endpoint the
frontend fetches after the case itself has rendered. See app/api/cases.py."""

from unittest.mock import patch

from app.services.case_service import case_service


def test_case_detail_never_calls_cognee(db_session, client, cognee_enabled):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")

    with patch.object(cognee_enabled, "recall") as mock_recall:
        resp = client.get(f"/api/cases/{case.id}")

    assert resp.status_code == 200
    mock_recall.assert_not_called()
    body = resp.json()
    assert body["memory"] == {"cognee_configured": True, "previous_interactions": [], "related_incidents": []}


def test_case_memory_endpoint_calls_cognee_when_configured(db_session, client, cognee_enabled):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    hits = [{"text": "Priya previously reported this payment issue.", "score": None, "metadata": {}}]

    with patch.object(cognee_enabled, "recall", return_value=hits) as mock_recall:
        resp = client.get(f"/api/cases/{case.id}/memory")

    assert resp.status_code == 200
    assert mock_recall.called
    body = resp.json()
    assert body["cognee_configured"] is True
    assert body["previous_interactions"] == [{"text": "Priya previously reported this payment issue.", "source": "Semantic memory"}]


def test_case_memory_endpoint_empty_when_not_configured(client):
    case_resp = client.post("/api/tickets", json={"customer_id": "CUST-001", "transaction_id": "TXN24001", "intent": "FAILED_PAYMENT"})
    case_id = case_resp.json()["ticket_id"]

    resp = client.get(f"/api/cases/{case_id}/memory")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"cognee_configured": False, "previous_interactions": [], "related_incidents": []}


def test_case_memory_endpoint_404_for_unknown_case(client):
    resp = client.get("/api/cases/CASE-DOES-NOT-EXIST/memory")
    assert resp.status_code == 404
