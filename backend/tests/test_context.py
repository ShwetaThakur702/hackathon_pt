from app.services.case_service import case_service
from app.services.transaction_service import transaction_service


def test_single_open_case_auto_associates(db_session):
    # CUST-001 has exactly one unresolved failed transaction (TXN24001).
    case, created = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    assert created is True

    match = transaction_service.find_relevant_transaction(db_session, "CUST-001", None, None, None)
    assert match.status == "FOUND"
    assert match.transaction["id"] == "TXN24001"


def test_multiple_open_cases_are_ambiguous(db_session):
    from datetime import date

    from app.models.transaction import Transaction

    db_session.add(
        Transaction(
            id="TXN24002", customer_id="CUST-001", amount=500, currency="INR", type="MERCHANT",
            merchant_name="Second Store", status="FAILED", debited=True, merchant_credited=False,
            refund_status="PENDING", transaction_date=date(2026, 9, 10),
        )
    )
    db_session.commit()

    case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    case_service.get_or_create_case(db_session, "CUST-001", "TXN24002", "FAILED_PAYMENT")

    match = transaction_service.find_relevant_transaction(db_session, "CUST-001", None, None, None)
    assert match.status == "AMBIGUOUS"
    assert {c["id"] for c in match.candidates} == {"TXN24001", "TXN24002"}


def test_explicit_amount_narrows_to_one_match(db_session):
    match = transaction_service.find_relevant_transaction(db_session, "CUST-001", None, 2400, None)
    assert match.status == "FOUND"
    assert match.transaction["id"] == "TXN24001"


def test_never_hallucinates_when_nothing_matches(db_session):
    match = transaction_service.find_relevant_transaction(db_session, "CUST-001", None, 999999, None)
    assert match.status == "NOT_FOUND"
