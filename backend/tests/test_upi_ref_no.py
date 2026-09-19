"""UPI Reference ID — the customer-facing 12-digit numeric reference (e.g.
"624718395021") that replaces the internal "TXN..." id everywhere the
frontend/chat shows a transaction reference to a customer."""

from app.integrations.llm.llm_service import llm_service
from app.services.transaction_service import transaction_service


def test_seeded_transaction_has_a_12_digit_upi_ref_no(db_session):
    txn = transaction_service.get_transaction(db_session, "TXN24001")
    assert txn is not None
    assert txn["upi_ref_no"] == "624718395021"
    assert len(txn["upi_ref_no"]) == 12
    assert txn["upi_ref_no"].isdigit()


def test_find_relevant_transaction_resolves_by_upi_ref_no(db_session):
    match = transaction_service.find_relevant_transaction(db_session, "CUST-001", "624718395021", None, None)
    assert match.status == "FOUND"
    assert match.transaction["id"] == "TXN24001"


def test_find_relevant_transaction_resolves_by_upi_ref_no_with_spaces(db_session):
    match = transaction_service.find_relevant_transaction(db_session, "CUST-001", "6247 1839 5021", None, None)
    assert match.status == "FOUND"
    assert match.transaction["id"] == "TXN24001"


def test_fallback_heuristic_extracts_upi_ref_no_not_amount():
    result = llm_service._fallback_understand("Meri payment ka UPI Ref No 624718395021 hai, abhi tak refund nahi mila")
    assert result["extracted_entities"]["transaction_id"] == "624718395021"
    # The 12-digit ref number must not also get misread as an amount.
    assert result["extracted_entities"]["amount"] is None


def test_fallback_heuristic_still_extracts_amount_when_no_ref_present():
    result = llm_service._fallback_understand("Mere 2400 kat gaye but payment fail dikha raha hai")
    assert result["extracted_entities"]["amount"] == 2400.0
    assert result["extracted_entities"]["transaction_id"] is None
