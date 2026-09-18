import uuid


def new_case_id() -> str:
    return f"CASE-{uuid.uuid4().hex[:6].upper()}"


def new_dispute_id() -> str:
    return f"DSP-{uuid.uuid4().hex[:6].upper()}"


def new_followup_id() -> str:
    return f"FUP-{uuid.uuid4().hex[:6].upper()}"
