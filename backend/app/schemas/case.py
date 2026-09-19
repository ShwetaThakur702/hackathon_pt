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
    """n8n's post-execution report (spec: "Report Result to Backend"). This
    is audit-only — n8n reports what the backend's own /execute-followup
    call already decided and did; it must never re-drive a case transition
    itself (that would make n8n a second decision-maker)."""

    case_id: str
    customer_id: str | None = None
    event_id: str | None = None
    correlation_id: str | None = None
    workflow_id: str | None = None
    result: str
    outcome: str | None = None
    action_taken: str | None = None
    current_compensation: float | None = None
    next_check_at: str | None = None
    transaction_status: str | None = None
    refund_status: str | None = None
    dispute_id: str | None = None
    secret: str | None = None


class NotifyCustomerRequest(BaseModel):
    case_id: str
    customer_id: str
    notification_type: str = "CASE_UPDATE"
    message: str
    secret: str | None = None
