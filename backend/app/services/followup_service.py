"""FollowupService — schedules async work and (when triggered) performs the
recheck -> evaluate_policy -> decide -> act loop (spec section 12.2/20.1).

`execute_due_followup` is the logic n8n's workflow calls into via
POST /api/workflows/execute-followup once the wait node fires. If n8n is not
configured (no N8N_WEBHOOK_URL — common for a judge who hasn't set up n8n
Cloud), the simulated-clock advance endpoint calls this function directly so
the autonomous loop remains fully demonstrable; either path runs the exact
same deterministic backend logic, so nothing about the *decision* is faked
(spec section 61) — only the transport that wakes it up differs.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.integrations.llm.llm_service import llm_service
from app.models.followup import Followup
from app.rules.engine import get_policy_engine
from app.services.audit_service import audit_service
from app.services.case_service import case_service
from app.services.dispute_service import dispute_service
from app.services.ids import new_followup_id
from app.services.memory_service import memory_service
from app.services.n8n_client import n8n_client
from app.services.notification_service import notification_service
from app.services.simulation_clock import simulation_clock_service
from app.services.transaction_service import transaction_service

policy_engine = get_policy_engine()


class FollowupService:
    def get_active_followup_for_case(self, db: Session, case_id: str) -> Followup | None:
        return (
            db.query(Followup)
            .filter(Followup.case_id == case_id, Followup.status.in_(["SCHEDULED", "RUNNING"]))
            .first()
        )

    def schedule(self, db: Session, case_id: str, scheduled_for: datetime, action: str = "RECHECK_FAILED_PAYMENT") -> tuple[Followup, bool]:
        existing = self.get_active_followup_for_case(db, case_id)
        if existing:
            return existing, False

        followup = Followup(id=new_followup_id(), case_id=case_id, scheduled_for=scheduled_for, status="SCHEDULED")
        db.add(followup)
        db.commit()
        db.refresh(followup)

        case = case_service.get_case(db, case_id)
        webhook_result = n8n_client.trigger_followup_scheduled(
            {
                "case_id": case_id,
                "customer_id": case.customer_id if case else None,
                "transaction_id": case.transaction_id if case else None,
                "followup_id": followup.id,
                "scheduled_for": scheduled_for.isoformat(),
                "action": action,
            }
        )

        audit_service.write_event(
            db,
            event_type="FOLLOW_UP_SCHEDULED",
            actor="AGENT",
            case_id=case_id,
            metadata={
                "followup_id": followup.id,
                "scheduled_for": scheduled_for.isoformat(),
                "n8n_triggered": webhook_result.get("triggered", False),
            },
        )
        return followup, True

    def get_due_followups(self, db: Session, as_of: datetime) -> list[Followup]:
        return db.query(Followup).filter(Followup.status == "SCHEDULED", Followup.scheduled_for <= as_of).all()

    def get_followup(self, db: Session, followup_id: str) -> Followup | None:
        return db.get(Followup, followup_id)

    def execute_due_followup(self, db: Session, followup_id: str) -> dict:
        followup = db.get(Followup, followup_id)
        if followup is None:
            return {"error": "followup_not_found"}
        if followup.status == "COMPLETED":
            return {"already_completed": True, "followup_id": followup_id}

        followup.status = "RUNNING"
        followup.attempt_count += 1
        followup.last_run_at = simulation_clock_service.now(db)
        db.commit()

        case = case_service.get_case(db, followup.case_id)
        if case is None:
            followup.status = "FAILED"
            db.commit()
            return {"error": "case_not_found"}

        audit_service.write_event(
            db, event_type="FOLLOW_UP_EXECUTED", actor="N8N", case_id=case.id,
            metadata={"followup_id": followup.id, "attempt": followup.attempt_count},
        )

        try:
            if case.status in ("WAITING_FOR_RESOLUTION", "DISPUTE_RAISED"):
                case_service.transition(db, case.id, "RECHECKING", actor="N8N")

            transaction = transaction_service.get_transaction(db, case.transaction_id) if case.transaction_id else None
            if transaction is None:
                raise RuntimeError("transaction_unavailable")

            audit_service.write_event(
                db, event_type="TRANSACTION_RECHECKED", actor="N8N", case_id=case.id,
                metadata={"transaction_id": transaction["id"], "refund_status": transaction["refund_status"]},
            )

            now = simulation_clock_service.now(db)
            policy_result = policy_engine.evaluate(transaction, now)
            audit_service.write_event(
                db, event_type="RULE_EVALUATED", actor="RULE_ENGINE", case_id=case.id,
                metadata=policy_result.to_dict(),
            )

            customer = _get_customer_language(db, case.customer_id)

            if transaction["refund_status"] == "RECEIVED" or not policy_result.applicable:
                case_service.transition(db, case.id, "RESOLVED", actor="AGENT", metadata={"reason": "refund_received"})
                message = llm_service.generate_response(
                    {"situation": "resolved"}, language=customer,
                )
                notification_service.notify_customer(db, case.customer_id, case.id, message)
                # Memory write point (spec section 8/39): follow-up result — resolved.
                memory_service.remember_resolution(db, case.id, transaction, "RESOLVED")
                result = {"result": "RESOLVED", "case_id": case.id}

            elif policy_result.is_breached:
                dispute, created = dispute_service.raise_dispute(
                    db, case.id, transaction["id"], reason="REFUND_DEADLINE_BREACHED",
                    compensation_amount=policy_result.compensation or 0,
                )
                if not created:
                    # Dispute already existed from an earlier day — recompute
                    # against today's overdue-day count so the penalty keeps
                    # accruing daily instead of freezing at day 1's amount.
                    dispute = dispute_service.update_compensation(db, dispute, policy_result.compensation or 0)
                case_service.transition(db, case.id, "DISPUTE_RAISED", actor="AGENT", metadata={"dispute_id": dispute.id})
                message = llm_service.generate_response(
                    {"situation": "dispute_raised", "compensation": policy_result.compensation or 0},
                    language=customer,
                )
                notification_service.notify_customer(db, case.customer_id, case.id, message)
                # Memory write point (spec section 8/39): follow-up result — dispute raised.
                memory_service.remember_resolution(
                    db, case.id, transaction, "DISPUTE_RAISED", policy_result.to_dict(), dispute_id=dispute.id
                )
                # Keep the loop alive: recheck again tomorrow so a still-open
                # dispute's compensation keeps growing and the case can still
                # resolve automatically once the refund lands. Mark this
                # followup COMPLETED first — schedule() dedups against any
                # SCHEDULED/RUNNING followup for the case, and this one is
                # still RUNNING at this point.
                followup.status = "COMPLETED"
                db.commit()
                self.schedule(db, case.id, now + timedelta(days=1))
                result = {"result": "DISPUTE_RAISED", "case_id": case.id, "dispute_id": dispute.id}

            else:
                # Not yet breached — keep waiting and schedule the next check
                # at the deadline instead of guessing.
                case_service.transition(db, case.id, "WAITING_FOR_RESOLUTION", actor="AGENT")
                deadline_dt = datetime.fromisoformat(policy_result.deadline) if policy_result.deadline else now
                self.schedule(db, case.id, deadline_dt)
                memory_service.remember_resolution(db, case.id, transaction, "STILL_PENDING", policy_result.to_dict())
                result = {"result": "STILL_PENDING", "case_id": case.id}

            followup.status = "COMPLETED"
            db.commit()
            return result

        except Exception as exc:
            followup.status = "FAILED"
            db.commit()
            audit_service.write_event(
                db, event_type="FOLLOW_UP_FAILED", actor="SYSTEM", case_id=case.id,
                metadata={"error": str(exc)},
            )
            try:
                case_service.transition(db, case.id, "HUMAN_ESCALATED", actor="SYSTEM", metadata={"reason": "followup_action_failed"})
            except Exception:
                pass
            return {"result": "FAILED", "case_id": case.id, "error": str(exc)}


def _get_customer_language(db: Session, customer_id: str) -> str:
    from app.models.customer import Customer

    customer = db.get(Customer, customer_id)
    return customer.preferred_language if customer else "English"


followup_service = FollowupService()
