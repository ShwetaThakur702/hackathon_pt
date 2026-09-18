"""Deterministic policy/rules engine.

This module is the single source of truth for financial policy math
(deadlines, compensation, breach detection). The LLM never computes these
values — see architectural Rule 1/2 in the spec. Nothing here is a claim
about real Paytm/RBI policy; it is prototype configuration only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

POLICIES_PATH = Path(__file__).parent / "policies.json"


@dataclass
class PolicyResult:
    policy_id: str
    rule_id: str | None
    applicable: bool
    deadline: str | None = None
    days_until_deadline: int | None = None
    days_overdue: int | None = None
    compensation_per_day: int | None = None
    compensation: int | None = None
    is_breached: bool = False
    recommended_action: str = "NONE"

    def to_dict(self) -> dict:
        return asdict(self)


class PolicyEngine:
    def __init__(self, policy_path: Path = POLICIES_PATH):
        self._policy = json.loads(Path(policy_path).read_text())

    @property
    def policy_id(self) -> str:
        return self._policy["policy_id"]

    @property
    def high_value_threshold(self) -> float:
        return self._policy["high_value_threshold"]

    @property
    def ombudsman_threshold_days(self) -> int:
        return self._policy["ombudsman_threshold_days"]

    def is_high_value(self, amount: float) -> bool:
        return amount >= self.high_value_threshold

    def evaluate(self, transaction: dict, current_time: datetime) -> PolicyResult:
        """Evaluate the failed-payment refund policy for a transaction.

        `transaction` is a plain dict with at least: type, debited,
        merchant_credited, transaction_date, status, refund_status.
        """
        txn_type = transaction.get("type")
        debited = bool(transaction.get("debited"))
        merchant_credited = transaction.get("merchant_credited")
        refund_status = transaction.get("refund_status")

        rule_cfg = self._policy["transaction_rules"].get(txn_type)

        applicable = bool(
            debited
            and merchant_credited is not True
            and rule_cfg is not None
            and refund_status != "RECEIVED"
        )

        if not applicable:
            return PolicyResult(
                policy_id=self.policy_id,
                rule_id=None,
                applicable=False,
                recommended_action="NONE" if refund_status != "RECEIVED" else "RESOLVE",
            )

        rule_id = f"{txn_type}_T_PLUS_{rule_cfg['deadline_days']}"

        txn_date = transaction.get("transaction_date")
        if isinstance(txn_date, str):
            txn_date = date.fromisoformat(txn_date)
        elif isinstance(txn_date, datetime):
            txn_date = txn_date.date()

        deadline_date = date.fromordinal(txn_date.toordinal() + rule_cfg["deadline_days"])
        today = current_time.date() if isinstance(current_time, datetime) else current_time

        delta_days = (deadline_date - today).days
        compensation_per_day = rule_cfg["compensation_per_day"]

        if delta_days > 0:
            return PolicyResult(
                policy_id=self.policy_id,
                rule_id=rule_id,
                applicable=True,
                deadline=deadline_date.isoformat(),
                days_until_deadline=delta_days,
                compensation_per_day=compensation_per_day,
                is_breached=False,
                recommended_action="FOLLOW_UP",
            )

        # delta_days <= 0: the deadline has been reached or passed. The
        # deadline day itself counts as the first day of breach (day 1) —
        # matches the demo narrative where "advance to deadline" already
        # triggers the dispute, not the day after.
        days_overdue = 1 if delta_days == 0 else (-delta_days + 1)
        compensation = days_overdue * compensation_per_day
        return PolicyResult(
            policy_id=self.policy_id,
            rule_id=rule_id,
            applicable=True,
            deadline=deadline_date.isoformat(),
            days_overdue=days_overdue,
            compensation_per_day=compensation_per_day,
            compensation=compensation,
            is_breached=True,
            recommended_action="RAISE_DISPUTE",
        )

    def is_ombudsman_eligible(self, case_created_at: datetime, current_time: datetime) -> bool:
        return (current_time.date() - case_created_at.date()).days >= self.ombudsman_threshold_days


_engine: PolicyEngine | None = None


def get_policy_engine() -> PolicyEngine:
    global _engine
    if _engine is None:
        _engine = PolicyEngine()
    return _engine
