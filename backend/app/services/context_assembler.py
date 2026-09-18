"""ContextAssembler — the single place that combines the database's
authoritative structured state with Cognee's semantic/historical memory into
one context dict for the agent (spec section 11).

The agent calls this through one tool (app.agent.tools.assemble_context), so
it never independently calls multiple unrelated memory systems itself.

DATABASE = authoritative structured state (customer, open cases, recent
transactions, recent messages) — unchanged from the original MemoryService
behavior.
COGNEE = best-effort semantic/historical narrative memory, additive only.
"""

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.services.memory_service import memory_service


class ContextAssembler:
    def assemble(self, db: Session, customer_id: str, current_message: str, current_case_id: str | None = None) -> dict:
        db_context = memory_service.get_customer_context(db, customer_id)

        semantic_memory: list[dict] = []
        customer = db.get(Customer, customer_id)
        if customer is not None:
            semantic_memory = memory_service.retrieve_customer_memory(db, customer_id, current_message)

        return {
            "customer": db_context.get("customer"),
            "customer_context": db_context,
            "active_cases": db_context.get("open_cases", []),
            "transaction_context": db_context.get("recent_transactions", []),
            "recent_conversation": db_context.get("recent_messages", []),
            "semantic_memory": semantic_memory,
        }


context_assembler = ContextAssembler()
