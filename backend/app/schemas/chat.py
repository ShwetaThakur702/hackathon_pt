from pydantic import BaseModel


class ChatRequest(BaseModel):
    customer_id: str
    message: str
    case_id: str | None = None


class ContextUsed(BaseModel):
    """Non-sensitive summary of what context the agent drew on for this
    turn (spec section 26). Never includes raw memory content — only
    whether/how much context was found."""

    previous_case_found: bool = False
    related_transaction_found: bool = False
    semantic_memory_hits: int = 0


class ChatResponse(BaseModel):
    case_id: str | None
    message: str
    intent: str | None
    status: str | None
    actions: list[str]
    context_used: ContextUsed | None = None
