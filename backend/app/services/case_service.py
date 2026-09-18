"""CaseService — the case state machine (spec section 19).

Invalid transitions are rejected. Every transition writes an audit event.
Database is the system of record (spec section 75): this is the only place
allowed to mutate `cases` rows.
"""

from sqlalchemy.orm import Session

from app.models.case import VALID_TRANSITIONS, Case
from app.services.audit_service import audit_service
from app.services.ids import new_case_id
from app.services.simulation_clock import simulation_clock_service


class InvalidTransitionError(Exception):
    pass


class CaseService:
    def get_case(self, db: Session, case_id: str) -> Case | None:
        return db.get(Case, case_id)

    def get_open_case_for_transaction(self, db: Session, customer_id: str, transaction_id: str) -> Case | None:
        return (
            db.query(Case)
            .filter(
                Case.customer_id == customer_id,
                Case.transaction_id == transaction_id,
                Case.status != "RESOLVED",
            )
            .order_by(Case.created_at.desc())
            .first()
        )

    def get_open_case_for_intent(self, db: Session, customer_id: str, intent: str) -> Case | None:
        """Dedup key for cases with no transaction (bills/FASTag/refunds —
        spec sections 16/17/19). Cases WITH a transaction dedup on that
        transaction instead (see get_open_case_for_transaction) since a
        customer can have several concurrent FAILED_PAYMENT cases."""
        return (
            db.query(Case)
            .filter(
                Case.customer_id == customer_id,
                Case.transaction_id.is_(None),
                Case.intent == intent,
                Case.status != "RESOLVED",
            )
            .order_by(Case.created_at.desc())
            .first()
        )

    def get_or_create_case(
        self, db: Session, customer_id: str, transaction_id: str | None, intent: str
    ) -> tuple[Case, bool]:
        """Idempotent case creation: reuses an already-open case for the
        same transaction (or, for a transaction-less case, the same intent)
        instead of creating a duplicate."""
        if transaction_id:
            existing = self.get_open_case_for_transaction(db, customer_id, transaction_id)
            if existing:
                return existing, False
        else:
            existing = self.get_open_case_for_intent(db, customer_id, intent)
            if existing:
                return existing, False

        case = Case(
            id=new_case_id(),
            customer_id=customer_id,
            transaction_id=transaction_id,
            intent=intent,
            status="NEW",
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        audit_service.write_event(
            db,
            event_type="COMPLAINT_RECEIVED",
            actor="SYSTEM",
            case_id=case.id,
            customer_id=customer_id,
            metadata={"intent": intent, "transaction_id": transaction_id},
        )
        return case, True

    def transition(
        self,
        db: Session,
        case_id: str,
        new_status: str,
        actor: str = "AGENT",
        metadata: dict | None = None,
    ) -> Case:
        case = db.get(Case, case_id)
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        if new_status != case.status:
            allowed = VALID_TRANSITIONS.get(case.status, set())
            if new_status not in allowed:
                raise InvalidTransitionError(
                    f"Cannot transition case {case_id} from {case.status} to {new_status}"
                )

        previous_status = case.status
        case.status = new_status
        if new_status == "RESOLVED":
            case.closed_at = simulation_clock_service.now(db)
        db.commit()
        db.refresh(case)

        audit_service.write_event(
            db,
            event_type="CASE_STATUS_CHANGED",
            actor=actor,
            case_id=case.id,
            customer_id=case.customer_id,
            metadata={"from": previous_status, "to": new_status, **(metadata or {})},
        )
        return case

    def _find_path(self, start: str, target: str) -> list[str] | None:
        """BFS over VALID_TRANSITIONS for the shortest forward hop sequence."""
        from collections import deque

        queue = deque([[start]])
        visited = {start}
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == target:
                return path[1:]
            for nxt in VALID_TRANSITIONS.get(node, set()):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append([*path, nxt])
        return None

    def advance_to(self, db: Session, case_id: str, target_status: str, actor: str = "AGENT", metadata: dict | None = None) -> Case:
        """Best-effort forward progression used by the agent pipeline.

        Unlike `transition`, an unreachable target is treated as a no-op
        (the case has already moved past this point in its lifecycle — e.g.
        a reused open case for a contextual follow-up) rather than an error.
        Use `transition` directly when a single-hop transition must be
        strictly validated (e.g. human override).
        """
        case = self.get_case(db, case_id)
        if case is None:
            raise ValueError(f"Case {case_id} not found")
        if case.status == target_status:
            return case
        path = self._find_path(case.status, target_status)
        if path is None:
            return case
        for step in path:
            case = self.transition(db, case_id, step, actor=actor, metadata=metadata if step == path[-1] else None)
        return case

    def update_fields(self, db: Session, case_id: str, **fields) -> Case:
        case = db.get(Case, case_id)
        if case is None:
            raise ValueError(f"Case {case_id} not found")
        for key, value in fields.items():
            setattr(case, key, value)
        db.commit()
        db.refresh(case)
        return case

    def list_cases(
        self, db: Session, status: str | None = None, priority: str | None = None, customer_id: str | None = None
    ) -> list[Case]:
        query = db.query(Case)
        if status:
            query = query.filter(Case.status == status)
        if priority:
            query = query.filter(Case.priority == priority)
        if customer_id:
            query = query.filter(Case.customer_id == customer_id)
        return query.order_by(Case.created_at.desc()).all()


case_service = CaseService()
