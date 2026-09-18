from typing import Any, TypedDict


class NishchintState(TypedDict, total=False):
    # Injected per-request, not part of the conceptual state but carried
    # through the graph since LangGraph nodes are pure functions of state.
    db: Any

    customer_id: str
    case_id: str | None

    user_message: str

    intent: str | None
    extracted_entities: dict
    contains_sensitive_credential: bool

    customer_context: dict
    transaction: dict | None
    transaction_match_status: str | None  # FOUND | AMBIGUOUS | NOT_FOUND
    transaction_candidates: list

    policy_result: dict | None

    decision: str | None
    next_action: str | None

    ticket_id: str | None
    is_new_case: bool
    followup_id: str | None
    dispute_id: str | None

    escalation_reason: str | None

    assistant_response: str | None

    actions_taken: list
    audit_events: list
