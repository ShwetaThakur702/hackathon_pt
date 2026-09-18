"""MemoryService — persistent customer/case/context retrieval.

Database-backed implementation for the prototype (spec section 17). All
methods below `save_interaction` are the original DB-only surface and are
unchanged — nothing here should ever be edited to become Cognee-dependent,
since the database must remain fully functional if Cognee is unavailable.

Below that, `remember_*`/`retrieve_*` are the Cognee-backed semantic-memory
extension: long-term contextual/narrative memory, layered ADDITIVELY on top
of the DB-backed methods above. Cognee is never the source of truth for a
transaction/policy/case fact — see docs/architecture.md. Every remember_*
call is best-effort and never raises (CogneeMemoryService itself never
raises); a Cognee outage degrades to "no semantic memory" silently, never to
a broken support workflow.
"""

from sqlalchemy.orm import Session

from app.integrations.cognee import memory_formatters as fmt
from app.integrations.cognee.cognee_memory_service import cognee_memory_service
from app.models.case import Case
from app.models.customer import Customer
from app.models.message import Message
from app.services.transaction_service import transaction_service


class MemoryService:
    def get_customer_context(self, db: Session, customer_id: str) -> dict:
        customer = db.get(Customer, customer_id)
        return {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "preferred_language": customer.preferred_language,
            }
            if customer
            else None,
            "recent_transactions": transaction_service.get_customer_transactions(db, customer_id),
            "open_cases": self.get_open_cases(db, customer_id),
            "recent_messages": self.get_previous_messages(db, customer_id),
        }

    def get_open_cases(self, db: Session, customer_id: str) -> list[dict]:
        rows = (
            db.query(Case)
            .filter(Case.customer_id == customer_id, Case.status != "RESOLVED")
            .order_by(Case.created_at.desc())
            .all()
        )
        return [
            {
                "id": c.id,
                "transaction_id": c.transaction_id,
                "intent": c.intent,
                "status": c.status,
                "deadline": c.deadline.isoformat() if c.deadline else None,
            }
            for c in rows
        ]

    def get_recent_transactions(self, db: Session, customer_id: str, limit: int = 10) -> list[dict]:
        return transaction_service.get_customer_transactions(db, customer_id, limit=limit)

    def get_previous_messages(self, db: Session, customer_id: str, limit: int = 20) -> list[dict]:
        case_ids = [c.id for c in db.query(Case.id).filter(Case.customer_id == customer_id).all()]
        if not case_ids:
            return []
        rows = (
            db.query(Message)
            .filter(Message.case_id.in_(case_ids))
            .order_by(Message.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {"case_id": m.case_id, "sender": m.sender, "message": m.message, "timestamp": m.timestamp.isoformat()}
            for m in reversed(rows)
        ]

    def save_interaction(self, db: Session, case_id: str, sender: str, message: str, language: str = "English") -> Message:
        row = Message(case_id=case_id, sender=sender, message=message, language=language)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    # ------------------------------------------------------------------
    # Cognee-backed semantic memory (additive; DB-only methods above are
    # never modified by this section). See module docstring.
    # ------------------------------------------------------------------

    def _now_label(self, db: Session) -> str:
        from app.services.simulation_clock import simulation_clock_service

        return simulation_clock_service.now(db).strftime("%d %B %Y")

    def remember_customer_interaction(
        self, db: Session, customer: Customer, case_id: str | None, intent: str | None, transaction: dict | None
    ) -> None:
        """Write point 1 (spec section 8): after a customer message is
        successfully processed. Never called with the raw message text —
        the graph already short-circuits sensitive-credential turns before
        a case exists, so there is no path for a secret to reach here."""
        if not cognee_memory_service.configured:
            return
        timestamp = self._now_label(db)
        text, category = fmt.format_customer_interaction(customer.name, intent or "UNKNOWN", transaction, case_id, timestamp)
        node_set = [f"customer:{customer.id}"] + ([f"case:{case_id}"] if case_id else [])
        cognee_memory_service.remember(text, category, {"customer_id": customer.id, "case_id": case_id}, node_set=node_set)

    def remember_case_event(
        self,
        db: Session,
        customer_name: str,
        case_id: str,
        transaction: dict | None,
        policy_result: dict | None = None,
        event_type: str = "CASE_CREATED",
        **extra,
    ) -> None:
        """Write points 2 and 5 (spec section 8): case created, human
        override."""
        if not cognee_memory_service.configured:
            return
        timestamp = self._now_label(db)
        if event_type == "HUMAN_OVERRIDE":
            text, category = fmt.format_human_override(
                case_id, extra.get("action", ""), extra.get("new_status"), extra.get("operator", "operator"),
                extra.get("note"), timestamp,
            )
        else:
            text, category = fmt.format_case_created(customer_name, case_id, transaction or {}, policy_result or {}, timestamp)
        node_set = [f"case:{case_id}"]
        if transaction and transaction.get("merchant_name"):
            node_set.append(f"merchant:{transaction['merchant_name']}")
        cognee_memory_service.remember(
            text, category,
            {"case_id": case_id, "transaction_id": (transaction or {}).get("id"), "event_type": event_type},
            node_set=node_set,
        )

    def remember_resolution(
        self, db: Session, case_id: str, transaction: dict | None, outcome: str,
        policy_result: dict | None = None, dispute_id: str | None = None,
    ) -> None:
        """Write points 4 and 6 (spec section 8): dispute raised / case
        resolved, including the follow-up recheck outcome that produced
        them."""
        if not cognee_memory_service.configured:
            return
        timestamp = self._now_label(db)
        if outcome == "DISPUTE_RAISED" and dispute_id:
            compensation = (policy_result or {}).get("compensation") or 0
            text, category = fmt.format_dispute_raised(case_id, dispute_id, transaction or {}, compensation, timestamp)
        elif outcome == "RESOLVED":
            text, category = fmt.format_case_resolved(case_id, transaction or {}, timestamp)
        else:
            text, category = fmt.format_followup_result(case_id, transaction or {}, outcome, policy_result, timestamp)
        cognee_memory_service.remember(
            text, category,
            {"case_id": case_id, "transaction_id": (transaction or {}).get("id"), "outcome": outcome},
            node_set=[f"case:{case_id}"],
        )

    def retrieve_customer_memory(self, db: Session, customer_id: str, query_text: str) -> list[dict]:
        """Used by ContextAssembler. Best-effort, never authoritative —
        see docs/architecture.md."""
        if not cognee_memory_service.configured:
            return []
        return cognee_memory_service.recall(f"Customer {customer_id}: {query_text}", node_name=[f"customer:{customer_id}"])

    def retrieve_case_memory(self, db: Session, case_id: str, query_text: str = "") -> list[dict]:
        if not cognee_memory_service.configured:
            return []
        query = query_text or f"History of case {case_id}"
        return cognee_memory_service.recall(query, node_name=[f"case:{case_id}"])

    def retrieve_related_incidents(self, db: Session, merchant_name: str) -> list[dict]:
        """Cross-customer semantic retrieval, e.g. for an operations-
        dashboard 'related incidents' view. Not a fraud-detection engine —
        just scoped semantic recall (spec section 13)."""
        if not cognee_memory_service.configured or not merchant_name:
            return []
        return cognee_memory_service.recall(
            f"Failed transactions or incidents involving merchant {merchant_name}", node_name=[f"merchant:{merchant_name}"]
        )


memory_service = MemoryService()
