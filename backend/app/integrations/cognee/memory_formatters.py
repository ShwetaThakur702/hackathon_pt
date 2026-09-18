"""Deterministic formatters that turn verified application state into clean
semantic-memory text for Cognee (spec: "Cognee should receive meaningful
support information... never fabricate facts... do not dump raw SQLAlchemy
objects").

Every formatter takes already-extracted, already-verified fields — never a
raw customer message and never a raw ORM row — so there's no path for a
credential or unverified LLM guess to end up in long-term memory. Content is
paraphrased from structured facts, matching the spec's own examples.
"""

from __future__ import annotations

CATEGORY_CUSTOMER_HISTORY = "customer_history"
CATEGORY_SUPPORT_CASE = "support_case"
CATEGORY_CONVERSATION = "conversation"
CATEGORY_TRANSACTION_CONTEXT = "transaction_context"
CATEGORY_MERCHANT_CONTEXT = "merchant_context"
CATEGORY_INCIDENT = "incident"
CATEGORY_RESOLUTION = "resolution"
CATEGORY_FOLLOWUP = "followup"


def _txn_label(transaction: dict | None) -> str:
    if not transaction:
        return "a transaction"
    merchant = transaction.get("merchant_name")
    amount = transaction.get("amount")
    if merchant:
        return f"₹{amount:.0f} payment at {merchant}"
    return f"₹{amount:.0f} P2P payment"


def format_customer_interaction(
    customer_name: str, intent: str, transaction: dict | None, case_id: str | None, timestamp: str
) -> tuple[str, str]:
    """A customer complaint/follow-up turn. Returns (text, category)."""
    if transaction:
        text = (
            f"On {timestamp}, {customer_name} reported an issue regarding "
            f"{_txn_label(transaction)} (transaction {transaction['id']}, case {case_id})."
        )
    else:
        text = f"On {timestamp}, {customer_name} sent a support message (intent: {intent}, case {case_id})."
    return text, CATEGORY_CONVERSATION


def format_case_created(customer_name: str, case_id: str, transaction: dict, policy_result: dict, timestamp: str) -> tuple[str, str]:
    deadline = policy_result.get("deadline")
    rule_id = policy_result.get("rule_id")
    text = (
        f"Case {case_id} was opened for {customer_name}: {_txn_label(transaction)} failed "
        f"(transaction {transaction['id']}). Applicable policy: {rule_id or 'n/a'}. "
        f"Expected refund date: {deadline or 'n/a'}. Opened on {timestamp}."
    )
    return text, CATEGORY_SUPPORT_CASE


def format_followup_result(case_id: str, transaction: dict, result: str, policy_result: dict | None, timestamp: str) -> tuple[str, str]:
    if result == "RESOLVED":
        text = f"On {timestamp}, case {case_id} ({_txn_label(transaction)}) was rechecked and the refund had arrived; the case was resolved."
    elif result == "DISPUTE_RAISED":
        compensation = (policy_result or {}).get("compensation") or 0
        text = (
            f"On {timestamp}, case {case_id} ({_txn_label(transaction)}) was rechecked; the refund "
            f"was still pending, so a dispute was raised with compensation ₹{compensation:.0f}."
        )
    else:
        text = f"On {timestamp}, case {case_id} ({_txn_label(transaction)}) was rechecked; the refund remained pending and the case continues to wait."
    return text, CATEGORY_FOLLOWUP


def format_dispute_raised(case_id: str, dispute_id: str, transaction: dict, compensation: float, timestamp: str) -> tuple[str, str]:
    text = (
        f"Dispute {dispute_id} was raised for case {case_id} ({_txn_label(transaction)}) on {timestamp} "
        f"after the refund deadline was breached. Compensation: ₹{compensation:.0f}."
    )
    return text, CATEGORY_RESOLUTION


def format_human_override(case_id: str, action: str, new_status: str | None, operator: str, note: str | None, timestamp: str) -> tuple[str, str]:
    detail = f" New status: {new_status}." if new_status else ""
    text = f"On {timestamp}, a human operator ({operator}) {action.lower()}d case {case_id}.{detail}"
    return text, CATEGORY_SUPPORT_CASE


def format_case_resolved(case_id: str, transaction: dict, timestamp: str) -> tuple[str, str]:
    text = f"Case {case_id} ({_txn_label(transaction)}) was resolved on {timestamp}."
    return text, CATEGORY_RESOLUTION


def format_merchant_incident(merchant_name: str, transaction_ids: list[str], timestamp: str) -> tuple[str, str]:
    text = (
        f"As of {timestamp}, {len(transaction_ids)} failed transactions have been observed for "
        f"merchant {merchant_name}: {', '.join(transaction_ids)}."
    )
    return text, CATEGORY_INCIDENT
