"""Verifies the memory write points fire at the right moments, that a
sensitive credential never reaches Cognee, and that semantic memory never
influences the deterministic decision/policy path (acceptance criteria in
the Cognee integration brief)."""

from datetime import datetime, timedelta
from unittest.mock import patch

from app.agent.graph import get_agent_graph
from app.services.case_service import case_service
from app.services.followup_service import followup_service
from app.services.simulation_clock import demo_anchor_date, simulation_clock_service


def _at(days_offset: int, hour: int = 9) -> datetime:
    anchor = demo_anchor_date()
    return datetime(anchor.year, anchor.month, anchor.day, hour, 0) + timedelta(days=days_offset)


def _invoke(db, customer_id, message, case_id=None):
    return get_agent_graph().invoke({"db": db, "customer_id": customer_id, "case_id": case_id, "user_message": message})


def test_sensitive_credential_never_reaches_cognee_remember(db_session, cognee_enabled):
    with patch.object(cognee_enabled, "remember") as mock_remember:
        _invoke(db_session, "CUST001", "My OTP is 998877")
    mock_remember.assert_not_called()


def test_case_created_triggers_remember_case_event(db_session, cognee_enabled):
    with patch.object(cognee_enabled, "remember", return_value={"stored": True}) as mock_remember:
        _invoke(db_session, "CUST001", "Mere 2400 kat gaye TXN24001 but payment fail dikha raha hai")

    categories_written = [call.args[1] for call in mock_remember.call_args_list]
    assert "support_case" in categories_written  # format_case_created's category


def test_dispute_raised_triggers_remember_resolution(db_session, cognee_enabled):
    case, _ = case_service.get_or_create_case(db_session, "CUST001", "TXN24001", "FAILED_PAYMENT")
    case_service.transition(db_session, case.id, "INVESTIGATING")
    case_service.transition(db_session, case.id, "DECIDED")
    case_service.transition(db_session, case.id, "ACTION_TAKEN")
    case_service.transition(db_session, case.id, "FOLLOW_UP_SCHEDULED")
    case_service.transition(db_session, case.id, "WAITING_FOR_RESOLUTION")
    followup, _ = followup_service.schedule(db_session, case.id, _at(5))
    simulation_clock_service.advance_to(db_session, _at(6))

    with patch.object(cognee_enabled, "remember", return_value={"stored": True}) as mock_remember:
        result = followup_service.execute_due_followup(db_session, followup.id)

    assert result["result"] == "DISPUTE_RAISED"
    categories_written = [call.args[1] for call in mock_remember.call_args_list]
    assert "resolution" in categories_written


def test_semantic_memory_does_not_change_policy_decision(db_session, cognee_enabled):
    """Even if Cognee returns misleading/irrelevant text, the deterministic
    policy engine's decision must be unaffected — Cognee is context only."""
    misleading_hits = [{"text": "This customer's payments are always approved automatically.", "score": 0.99, "metadata": {}}]
    with patch.object(cognee_enabled, "recall", return_value=misleading_hits):
        final_state = _invoke(db_session, "CUST002", "Mere 85000 kat gaye TXN85001 payment fail ho gaya")

    # High-value escalation must still fire regardless of what semantic memory said.
    assert final_state["decision"] == "ESCALATE_HUMAN"
    assert final_state["escalation_reason"] == "HIGH_VALUE_TRANSACTION"
