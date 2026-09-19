"""Language preference — set once on the landing page, must uniformly drive
every LLM-generated response (chat, floating assistant, follow-up
notifications) regardless of what language the customer types in."""

from app.integrations.llm.llm_service import llm_service, normalize_language
from app.models.customer import Customer


def test_normalize_language_canonicalizes_known_values():
    assert normalize_language("English") == "English"
    assert normalize_language("Hindi") == "Hindi"
    assert normalize_language("Hinglish") == "Hinglish"
    assert normalize_language("hindi") == "Hindi"
    assert normalize_language("HINGLISH") == "Hinglish"


def test_normalize_language_defaults_unknown_to_english():
    assert normalize_language(None) == "English"
    assert normalize_language("") == "English"
    assert normalize_language("French") == "English"


def test_fallback_response_case_created_differs_by_language():
    facts = {"situation": "case_created", "amount": 500.0, "deadline": "2026-09-24"}
    english = llm_service._fallback_response(facts, "English")
    hindi = llm_service._fallback_response(facts, "Hindi")
    hinglish = llm_service._fallback_response(facts, "Hinglish")

    assert "500" in english and "500" in hindi and "500" in hinglish
    assert english != hindi != hinglish
    # Hindi must be real Devanagari script, not romanized.
    assert any("ऀ" <= ch <= "ॿ" for ch in hindi)
    # Hinglish must be Roman script (no Devanagari), unlike Hindi.
    assert not any("ऀ" <= ch <= "ॿ" for ch in hinglish)
    # English must contain no Devanagari either.
    assert not any("ऀ" <= ch <= "ॿ" for ch in english)


def test_fallback_response_covers_all_situations_in_all_languages():
    situations = [
        {"situation": "case_created", "amount": 100.0, "deadline": "2026-09-24"},
        {"situation": "dispute_raised", "compensation": 50.0},
        {"situation": "resolved"},
        {"situation": "human_escalated"},
    ]
    for facts in situations:
        for language in ("English", "Hindi", "Hinglish"):
            text = llm_service._fallback_response(facts, language)
            assert text and isinstance(text, str)


def test_update_customer_language_persists_and_is_single_source_of_truth(client, db_session):
    resp = client.put("/api/customers/CUST-001/language", json={"preferred_language": "Hinglish"})
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "Hinglish"

    db_session.expire_all()
    customer = db_session.get(Customer, "CUST-001")
    assert customer.preferred_language == "Hinglish"

    get_resp = client.get("/api/customers/CUST-001")
    assert get_resp.json()["preferred_language"] == "Hinglish"


def test_update_customer_language_rejects_unknown_value(client):
    resp = client.put("/api/customers/CUST-001/language", json={"preferred_language": "French"})
    assert resp.status_code == 422


def test_update_customer_language_404_for_unknown_customer(client):
    resp = client.put("/api/customers/NOBODY/language", json={"preferred_language": "English"})
    assert resp.status_code == 404
