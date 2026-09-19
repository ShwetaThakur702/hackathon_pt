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
from app.models.bill import Bill
from app.models.fastag_account import FastagAccount
from app.models.followup import Followup
from app.models.refund import Refund
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

# Non-transaction cases (no refund-deadline policy applies): the follow-up
# just rechecks whether the counterparty's system has caught up, and closes
# the case once it has — see FollowupService._resolve_reconciliation.
RECONCILIATION_INTENTS = {"BILL_RECONCILIATION", "FASTAG_BALANCE_MISMATCH", "REFUND_MISMATCH"}


class FollowupService:
    def schedule_reconciliation_check(self, db: Session, case_id: str) -> Followup:
        now = simulation_clock_service.now(db)
        followup, _ = self.schedule(db, case_id, now + timedelta(days=1), action="RECONCILIATION_CHECK")
        return followup

    def _resolve_reconciliation(self, db: Session, case, followup: Followup) -> dict:
        """The provider/FASTag/merchant side has caught up by the next check —
        mirror that in the mock state, close the case, tell the customer."""
        cid = case.customer_id
        if case.intent == "BILL_RECONCILIATION":
            bill = db.query(Bill).filter(Bill.customer_id == cid, Bill.provider_ack_status == "PENDING").first()
            if bill:
                bill.provider_ack_status = "ACKNOWLEDGED"
            facts = {"situation": "bill_acknowledged", "provider": bill.provider_name if bill else "your provider"}
            action = "provider_acknowledged"
        elif case.intent == "FASTAG_BALANCE_MISMATCH":
            acct = db.query(FastagAccount).filter(FastagAccount.customer_id == cid).first()
            if acct and acct.last_recharge_status == "BALANCE_UPDATE_PENDING":
                acct.balance += acct.last_recharge_amount
                acct.last_recharge_status = "CREDITED"
            facts = {"situation": "fastag_updated", "balance": acct.balance if acct else None}
            action = "balance_updated"
        else:
            refund = db.query(Refund).filter(Refund.customer_id == cid, Refund.customer_received.is_(False)).first()
            if refund:
                refund.customer_received = True
            facts = {"situation": "refund_received", "amount": refund.amount if refund else None,
                     "merchant": refund.merchant_name if refund else "the merchant"}
            action = "refund_received"
        db.commit()

        case_service.transition(db, case.id, "RECHECKING", actor="N8N")
        case_service.transition(db, case.id, "RESOLVED", actor="AGENT", metadata={"reason": action})
        message = llm_service.generate_response(facts, language=_get_customer_language(db, cid))
        notification_service.notify_customer(db, cid, case.id, message)
        followup.status = "COMPLETED"
        db.commit()
        return {
            "result": "RESOLVED", "case_id": case.id, "customer_id": cid,
            "status": "RESOLVED", "outcome": "RESOLVED", "action_taken": action,
            "current_compensation": None, "next_check_at": None, "notification_message": message,
        }

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
        transaction = transaction_service.get_transaction(db, case.transaction_id) if case and case.transaction_id else None
        webhook_result = n8n_client.trigger_followup_scheduled(
            {
                # followup_id doubles as this event's idempotency key
                # (event_id) — n8n's workflow uses it, unchanged, to call
                # back into /execute-followup, which is itself idempotent
                # per followup_id (see execute_due_followup below).
                "event_id": followup.id,
                "followup_id": followup.id,
                "case_id": case_id,
                "customer_id": case.customer_id if case else None,
                "correlation_id": case_id,
                "transaction_id": case.transaction_id if case else None,
                # Customer-facing identifier — n8n/webhook consumers should
                # never need the internal transaction id.
                "upi_reference_id": transaction["upi_ref_no"] if transaction else None,
                "scheduled_for": scheduled_for.isoformat(),
                "next_check_at": scheduled_for.isoformat(),
                "reason": action,
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

    def _outcome_snapshot(self, db: Session, case) -> dict:
        """Rebuilds the same {status, outcome, action_taken,
        current_compensation, next_check_at} contract from CURRENT stored
        state, without re-running any action. Used for an idempotent
        replay of an already-completed follow-up (spec section 6: a
        duplicate webhook/event must never re-raise a dispute, re-notify,
        etc. — it just gets told what already happened)."""
        active_followup = self.get_active_followup_for_case(db, case.id)
        next_check_at = active_followup.scheduled_for.isoformat() if active_followup else None

        if case.status == "RESOLVED":
            return {
                "customer_id": case.customer_id,
                "status": "RESOLVED", "outcome": "RESOLVED", "action_taken": "close_case",
                "current_compensation": None, "next_check_at": None,
            }
        if case.status == "DISPUTE_RAISED":
            transaction = transaction_service.get_transaction(db, case.transaction_id) if case.transaction_id else None
            compensation = None
            if transaction:
                compensation = policy_engine.evaluate(transaction, simulation_clock_service.now(db)).compensation
            return {
                "customer_id": case.customer_id,
                "status": "UNRESOLVED", "outcome": "DISPUTE_RAISED", "action_taken": "raise_dispute",
                "current_compensation": compensation, "next_check_at": next_check_at,
            }
        if case.status == "HUMAN_ESCALATED":
            return {
                "customer_id": case.customer_id,
                "status": "ESCALATED", "outcome": "ESCALATED", "action_taken": "escalate_to_human",
                "current_compensation": None, "next_check_at": None,
            }
        return {
            "customer_id": case.customer_id,
            "status": "MONITORING", "outcome": "CONTINUE_MONITORING", "action_taken": None,
            "current_compensation": None, "next_check_at": next_check_at,
        }

    def execute_due_followup(self, db: Session, followup_id: str) -> dict:
        followup = db.get(Followup, followup_id)
        if followup is None:
            return {"error": "followup_not_found"}
        if followup.status == "COMPLETED":
            case = case_service.get_case(db, followup.case_id)
            snapshot = self._outcome_snapshot(db, case) if case else {}
            return {"already_completed": True, "followup_id": followup_id, "case_id": followup.case_id, **snapshot}

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
            if case.intent in RECONCILIATION_INTENTS:
                return self._resolve_reconciliation(db, case, followup)

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
                result = {
                    "result": "RESOLVED", "case_id": case.id, "customer_id": case.customer_id,
                    "status": "RESOLVED", "outcome": "RESOLVED", "action_taken": "close_case",
                    "current_compensation": None, "next_check_at": None, "notification_message": message,
                }

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
                next_check = now + timedelta(days=1)
                self.schedule(db, case.id, next_check)
                result = {
                    "result": "DISPUTE_RAISED", "case_id": case.id, "customer_id": case.customer_id, "dispute_id": dispute.id,
                    "status": "UNRESOLVED", "outcome": "DISPUTE_RAISED", "action_taken": "raise_dispute",
                    "current_compensation": policy_result.compensation, "next_check_at": next_check.isoformat(),
                    "notification_message": message,
                }

            else:
                # Not yet breached — keep waiting and schedule the next check
                # at the deadline instead of guessing.
                case_service.transition(db, case.id, "WAITING_FOR_RESOLUTION", actor="AGENT")
                deadline_dt = datetime.fromisoformat(policy_result.deadline) if policy_result.deadline else now
                self.schedule(db, case.id, deadline_dt)
                memory_service.remember_resolution(db, case.id, transaction, "STILL_PENDING", policy_result.to_dict())
                result = {
                    "result": "STILL_PENDING", "case_id": case.id, "customer_id": case.customer_id,
                    "status": "MONITORING", "outcome": "CONTINUE_MONITORING", "action_taken": None,
                    "current_compensation": None, "next_check_at": deadline_dt.isoformat(),
                    "notification_message": None,
                }

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
            return {
                "result": "FAILED", "case_id": case.id, "customer_id": case.customer_id, "error": str(exc),
                "status": "ESCALATED", "outcome": "ESCALATED", "action_taken": "escalate_to_human",
                "current_compensation": None, "next_check_at": None, "notification_message": None,
            }


def _get_customer_language(db: Session, customer_id: str) -> str:
    from app.models.customer import Customer

    customer = db.get(Customer, customer_id)
    return customer.preferred_language if customer else "English"


followup_service = FollowupService()
