from datetime import datetime

from app.rules.engine import PolicyEngine

engine = PolicyEngine()


def _txn(**overrides):
    base = {
        "type": "MERCHANT",
        "debited": True,
        "merchant_credited": False,
        "refund_status": "PENDING",
        "transaction_date": "2026-09-10",
    }
    base.update(overrides)
    return base


def test_merchant_deadline_is_t_plus_5():
    result = engine.evaluate(_txn(), datetime(2026, 9, 10))
    assert result.rule_id == "MERCHANT_T_PLUS_5"
    assert result.deadline == "2026-09-15"


def test_person_deadline_is_t_plus_1():
    result = engine.evaluate(_txn(type="PERSON"), datetime(2026, 9, 10))
    assert result.rule_id == "PERSON_T_PLUS_1"
    assert result.deadline == "2026-09-11"


def test_deadline_uses_calendar_days_not_business_days():
    # 2026-09-10 is a Thursday; T+1 lands on a Friday either way, so use a
    # span that would differ under business-day math to prove calendar math.
    result = engine.evaluate(_txn(type="MERCHANT", transaction_date="2026-09-11"), datetime(2026, 9, 11))
    assert result.deadline == "2026-09-16"


def test_not_yet_breached_before_deadline():
    result = engine.evaluate(_txn(), datetime(2026, 9, 12))
    assert result.is_breached is False
    assert result.days_until_deadline == 3
    assert result.recommended_action == "FOLLOW_UP"


def test_breached_on_deadline_day_itself():
    # The demo narrative (spec section 22) advances the clock exactly to the
    # deadline and expects the dispute to already be raised at that point.
    result = engine.evaluate(_txn(), datetime(2026, 9, 15))
    assert result.is_breached is True
    assert result.days_overdue == 1
    assert result.compensation == 100
    assert result.recommended_action == "RAISE_DISPUTE"


def test_breach_and_compensation_after_deadline():
    result = engine.evaluate(_txn(), datetime(2026, 9, 16))
    assert result.is_breached is True
    assert result.days_overdue == 2
    assert result.compensation == 200
    assert result.recommended_action == "RAISE_DISPUTE"


def test_multi_day_overdue_compensation_accrues_per_day():
    result = engine.evaluate(_txn(), datetime(2026, 9, 18))
    assert result.days_overdue == 4
    assert result.compensation == 400


def test_not_applicable_when_refund_already_received():
    result = engine.evaluate(_txn(refund_status="RECEIVED"), datetime(2026, 9, 20))
    assert result.applicable is False


def test_high_value_threshold():
    assert engine.is_high_value(50000) is True
    assert engine.is_high_value(49999) is False
