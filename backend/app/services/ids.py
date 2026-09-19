import random
import uuid


def new_case_id() -> str:
    return f"CASE-{uuid.uuid4().hex[:6].upper()}"


def new_transaction_id() -> str:
    return f"TXN{uuid.uuid4().hex[:8].upper()}"


def new_upi_ref_no() -> str:
    """A realistic-looking 12-digit numeric UPI Reference ID — first digit
    non-zero, like a real UPI transaction reference."""
    return str(random.randint(1, 9)) + "".join(str(random.randint(0, 9)) for _ in range(11))


def new_dispute_id() -> str:
    return f"DSP-{uuid.uuid4().hex[:6].upper()}"


def new_followup_id() -> str:
    return f"FUP-{uuid.uuid4().hex[:6].upper()}"
