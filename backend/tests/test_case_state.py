import pytest

from app.services.case_service import InvalidTransitionError, case_service


def test_valid_transition_succeeds(db_session):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    assert case.status == "NEW"
    case = case_service.transition(db_session, case.id, "INVESTIGATING")
    assert case.status == "INVESTIGATING"


def test_invalid_transition_is_rejected(db_session):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    with pytest.raises(InvalidTransitionError):
        case_service.transition(db_session, case.id, "RESOLVED")


def test_resolved_case_has_no_further_transitions(db_session):
    case, _ = case_service.get_or_create_case(db_session, "CUST-001", "TXN24001", "FAILED_PAYMENT")
    case_service.transition(db_session, case.id, "INVESTIGATING")
    case_service.transition(db_session, case.id, "DECIDED")
    case_service.transition(db_session, case.id, "ACTION_TAKEN")
    case_service.transition(db_session, case.id, "RESOLVED")
    with pytest.raises(InvalidTransitionError):
        case_service.transition(db_session, case.id, "DISPUTE_RAISED")
