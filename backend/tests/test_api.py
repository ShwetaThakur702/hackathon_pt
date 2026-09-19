def test_health(client):
    assert client.get("/health").status_code == 200


def test_chat_creates_case_and_schedules_followup(client):
    resp = client.post(
        "/chat",
        json={"customer_id": "CUST-001", "message": "Mere 2400 kat gaye TXN24001 but payment fail dikha raha hai", "case_id": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] is not None
    assert "FOLLOWUP_SCHEDULED" in body["actions"] or "TICKET_CREATED" in body["actions"]

    case_resp = client.get(f"/api/cases/{body['case_id']}")
    assert case_resp.status_code == 200
    case = case_resp.json()
    assert case["followup"] is not None
    assert case["transaction"]["id"] == "TXN24001"


def test_contextual_followup_reuses_existing_case(client):
    first = client.post(
        "/chat",
        json={"customer_id": "CUST-001", "message": "Mere 2400 kat gaye TXN24001 but payment fail dikha raha hai", "case_id": None},
    ).json()

    second = client.post(
        "/chat", json={"customer_id": "CUST-001", "message": "Abhi tak paise nahi aaye", "case_id": None}
    ).json()

    assert second["case_id"] == first["case_id"]


def test_get_transaction(client):
    resp = client.get("/api/transactions/TXN24001")
    assert resp.status_code == 200
    assert resp.json()["amount"] == 2400


def test_create_dispute_endpoint(client):
    ticket = client.post("/api/tickets", json={"customer_id": "CUST-001", "transaction_id": "TXN24001", "intent": "FAILED_PAYMENT"}).json()
    resp = client.post(
        "/api/disputes",
        json={"case_id": ticket["ticket_id"], "transaction_id": "TXN24001", "reason": "REFUND_DEADLINE_BREACHED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RAISED"


def test_followups_endpoint(client):
    ticket = client.post("/api/tickets", json={"customer_id": "CUST-001", "transaction_id": "TXN24001", "intent": "FAILED_PAYMENT"}).json()
    # Arbitrary future timestamp — this test only checks create+fetch
    # round-tripping, not policy math, so it doesn't need to be anchored
    # to "today" like the seed data / other followup tests are.
    resp = client.post("/api/followups", json={"case_id": ticket["ticket_id"], "scheduled_for": "2027-01-15T09:00:00"})
    assert resp.status_code == 200
    followup_id = resp.json()["followup_id"]

    get_resp = client.get(f"/api/followups/{followup_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "SCHEDULED"


def test_simulation_advance_and_reset(client):
    resp = client.post("/api/simulate/advance-time", json={"days": 1})
    assert resp.status_code == 200
    assert "current_time" in resp.json()

    reset_resp = client.post("/api/simulate/reset")
    assert reset_resp.status_code == 200


def test_end_to_end_advance_to_deadline_raises_dispute(client):
    chat_resp = client.post(
        "/chat",
        json={"customer_id": "CUST-001", "message": "Mere 2400 kat gaye TXN24001 but payment fail dikha raha hai", "case_id": None},
    ).json()

    advance_resp = client.post("/api/simulate/advance-to-deadline")
    assert advance_resp.status_code == 200

    case = client.get(f"/api/cases/{chat_resp['case_id']}").json()
    assert case["status"] == "DISPUTE_RAISED"
    assert case["dispute"] is not None
