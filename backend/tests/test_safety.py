import json

from app.integrations.llm.llm_service import contains_sensitive_credential
from app.models.audit import AuditLog


def test_otp_is_detected():
    assert contains_sensitive_credential("My OTP is 1234") is True


def test_upi_pin_is_detected():
    assert contains_sensitive_credential("mera UPI PIN 5566 hai") is True


def test_normal_message_is_not_flagged():
    assert contains_sensitive_credential("Mere 2400 kat gaye but payment fail ho gaya") is False


def test_chat_warns_and_does_not_store_secret(client):
    resp = client.post("/chat", json={"customer_id": "CUST001", "message": "My OTP is 998877", "case_id": None})
    assert resp.status_code == 200
    body = resp.json()
    assert "OTP" in body["message"] or "otp" in body["message"].lower()

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        events = db.query(AuditLog).filter(AuditLog.event_type == "SENSITIVE_CREDENTIAL_DETECTED").all()
        assert len(events) == 1
        for event in events:
            assert "998877" not in event.metadata_json
        # no audit metadata anywhere should contain the raw secret
        all_events = db.query(AuditLog).all()
        for event in all_events:
            assert "998877" not in json.dumps(event.metadata_json)
    finally:
        db.close()
