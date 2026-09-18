from pydantic import BaseModel


class TicketCreateRequest(BaseModel):
    customer_id: str
    transaction_id: str | None = None
    intent: str = "FAILED_PAYMENT"


class DisputeCreateRequest(BaseModel):
    case_id: str
    transaction_id: str
    reason: str


class FollowupCreateRequest(BaseModel):
    case_id: str
    scheduled_for: str


class HumanOverrideRequest(BaseModel):
    action: str  # APPROVE | OVERRIDE
    new_status: str | None = None
    note: str | None = None
    operator: str = "operator"


class WorkflowResultCallback(BaseModel):
    case_id: str
    workflow_id: str | None = None
    result: str
    transaction_status: str | None = None
    refund_status: str | None = None
    dispute_id: str | None = None
    secret: str | None = None
