"""The Send Money hero demo flow: Home -> Send Money -> pick a recipient ->
enter an amount -> Pay. The backend, not React state, decides and persists
the outcome (spec: "Do NOT simulate this only in React state")."""


def test_paying_apollo_medicals_fails_and_debits_with_a_real_upi_ref(client):
    resp = client.post(
        "/api/payments/send",
        json={"customer_id": "CUST-001", "recipient_name": "Apollo Medicals", "recipient_type": "MERCHANT", "amount": 2400},
    )
    assert resp.status_code == 200
    txn = resp.json()
    assert txn["status"] == "FAILED"
    assert txn["debited"] is True
    assert txn["merchant_credited"] is False
    assert txn["refund_status"] == "PENDING"
    assert txn["upi_ref_no"].isdigit()
    assert len(txn["upi_ref_no"]) == 12

    # Persisted for real — not just returned in the response.
    fetched = client.get(f"/api/transactions/{txn['id']}").json()
    assert fetched == txn


def test_paying_a_p2p_contact_succeeds(client):
    resp = client.post(
        "/api/payments/send",
        json={"customer_id": "CUST-001", "recipient_name": "Rohit", "recipient_type": "CONTACT", "amount": 500},
    )
    assert resp.status_code == 200
    txn = resp.json()
    assert txn["status"] == "SUCCESS"
    assert txn["merchant_credited"] is True
    assert txn["type"] == "PERSON"


def test_each_payment_gets_a_distinct_transaction_and_upi_ref(client):
    first = client.post(
        "/api/payments/send",
        json={"customer_id": "CUST-001", "recipient_name": "Apollo Medicals", "recipient_type": "MERCHANT", "amount": 2400},
    ).json()
    second = client.post(
        "/api/payments/send",
        json={"customer_id": "CUST-001", "recipient_name": "Apollo Medicals", "recipient_type": "MERCHANT", "amount": 2400},
    ).json()
    assert first["id"] != second["id"]
    assert first["upi_ref_no"] != second["upi_ref_no"]


def test_a_failed_payment_immediately_surfaces_as_a_proactive_attention_item(client):
    txn = client.post(
        "/api/payments/send",
        json={"customer_id": "CUST-001", "recipient_name": "Apollo Medicals", "recipient_type": "MERCHANT", "amount": 2400},
    ).json()

    attention = client.get("/api/nishchint/attention", params={"customer_id": "CUST-001"}).json()
    matching = [i for i in attention["items"] if i.get("id") == txn["id"]]
    assert len(matching) == 1
    assert matching[0]["type"] == "TRANSACTION"
    assert matching[0]["cta_href"] == f"/transactions/{txn['id']}"
