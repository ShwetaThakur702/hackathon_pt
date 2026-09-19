import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.graph import get_agent_graph
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.chat import ChatRequest, ChatResponse, ContextUsed
from app.services.case_service import case_service
from app.services.memory_service import memory_service

logger = logging.getLogger("nishchint.chat")

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Unknown customer_id {payload.customer_id}")

    graph = get_agent_graph()
    try:
        final_state = graph.invoke(
            {
                "db": db,
                "customer_id": payload.customer_id,
                "case_id": payload.case_id,
                "user_message": payload.message,
                "preferred_language": customer.preferred_language,
            }
        )
    except Exception:
        logger.exception("Agent graph failed for customer_id=%s", payload.customer_id)
        # spec section 43: never crash, never claim success on failure.
        return ChatResponse(
            case_id=payload.case_id,
            message="I'm unable to process your request right now. I've kept your case open and routed it for review.",
            intent=None,
            status=None,
            actions=[],
        )

    case_id = final_state.get("case_id")
    status = None
    if case_id:
        case = case_service.get_case(db, case_id)
        status = case.status if case else None
        memory_service.save_interaction(db, case_id, "CUSTOMER", payload.message, customer.preferred_language)
        memory_service.save_interaction(db, case_id, "ASSISTANT", final_state.get("assistant_response", ""), customer.preferred_language)

        # Memory write point 1 (spec section 8): after a customer message is
        # successfully processed. Backgrounded so a Cognee Cloud round trip
        # never adds latency to the customer-facing response; the DB writes
        # above (system of record) already happened synchronously.
        background_tasks.add_task(
            memory_service.remember_customer_interaction,
            db, customer, case_id, final_state.get("intent"), final_state.get("transaction"),
        )

    semantic_hits = (final_state.get("customer_context") or {}).get("semantic_memory") or []
    context_used = ContextUsed(
        previous_case_found=bool(case_id) and not final_state.get("is_new_case", False),
        related_transaction_found=final_state.get("transaction") is not None,
        semantic_memory_hits=len(semantic_hits),
    )

    return ChatResponse(
        case_id=case_id,
        message=final_state.get("assistant_response", ""),
        intent=final_state.get("intent"),
        status=status,
        actions=final_state.get("actions_taken", []),
        context_used=context_used,
    )
