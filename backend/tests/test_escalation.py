def test_high_value_transaction_escalates_to_human(client):
    resp = client.post(
        "/chat",
        json={"customer_id": "CUST002", "message": "Mere 85000 kat gaye TXN85001 payment fail ho gaya", "case_id": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] is not None

    case_resp = client.get(f"/api/cases/{body['case_id']}")
    assert case_resp.status_code == 200
    case = case_resp.json()
    assert case["status"] == "HUMAN_ESCALATED"
    assert case["escalation_reason"] == "HIGH_VALUE_TRANSACTION"


def test_normal_value_transaction_does_not_escalate(client):
    resp = client.post(
        "/chat",
        json={"customer_id": "CUST001", "message": "Mere 2400 kat gaye TXN24001 but payment fail dikha raha hai", "case_id": None},
    )
    body = resp.json()
    case_resp = client.get(f"/api/cases/{body['case_id']}")
    case = case_resp.json()
    assert case["status"] != "HUMAN_ESCALATED"
