"""Seed Cognee Cloud with the demo's historical memory (spec section 30/44).

Run this once before a demo/judging session, after the app's own database
has been seeded (either via `POST /simulate/reset` or on first backend
startup) so Priya's CUST-001/TXN24001 case already exists.

This does NOT touch the application database — it only writes semantic
memory via MemoryService, exactly the same write path the live app uses.
Re-running is safe: Cognee merges semantically similar content into the
same graph nodes rather than erroring, though it is not a strict
dedup guarantee — see reset_cognee_demo.py for a clean slate.

Usage:
    cd backend
    source .venv/bin/activate
    python -m scripts.seed_cognee
"""

import sys

from app.config import cognee_configured, get_settings
from app.database.session import SessionLocal
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.rules.engine import get_policy_engine
from app.services.memory_service import memory_service
from app.services.simulation_clock import simulation_clock_service


def _transaction_dict(txn: Transaction) -> dict:
    return {
        "id": txn.id, "amount": txn.amount, "type": txn.type, "merchant_name": txn.merchant_name,
        "refund_status": txn.refund_status, "transaction_date": txn.transaction_date.isoformat(),
    }


def main() -> int:
    settings = get_settings()
    if not cognee_configured(settings):
        print("Cognee is not configured (COGNEE_ENABLED/COGNEE_API_KEY/COGNEE_BASE_URL) — nothing to seed.")
        return 1

    db = SessionLocal()
    policy_engine = get_policy_engine()
    try:
        priya = db.get(Customer, "CUST-001")
        txn = db.get(Transaction, "TXN24001")
        if priya is None or txn is None:
            print("CUST-001/TXN24001 not found — run POST /simulate/reset (or start the backend once) first.")
            return 1

        now = simulation_clock_service.now(db)
        txn_dict = _transaction_dict(txn)
        policy_result = policy_engine.evaluate(txn_dict, now).to_dict()

        print("Seeding Priya's historical case-created memory (TXN24001)...")
        memory_service.remember_case_event(db, priya.name, "CASE-SEED-DEMO", txn_dict, policy_result, event_type="CASE_CREATED")

        print("Seeding synthetic Apollo Medicals merchant-incident memories for related-incident demo...")
        # Synthetic, display-name-only — not real seeded customers (the demo
        # ships exactly one, Priya/CUST-001). This is purely to demonstrate
        # Cognee's cross-customer "other people had this same merchant
        # issue" related-incident retrieval on the case page; it never
        # touches the application database's Customer table.
        for other_customer_name, fake_case_id, amount in [
            ("Other Customer A", "CASE-SEED-INCIDENT-1", 1800),
            ("Other Customer B", "CASE-SEED-INCIDENT-2", 2200),
        ]:
            synthetic_txn = {
                "id": f"{fake_case_id}-TXN", "amount": amount, "type": "MERCHANT",
                "merchant_name": "Apollo Medicals", "refund_status": "PENDING", "transaction_date": txn.transaction_date.isoformat(),
            }
            memory_service.remember_case_event(db, other_customer_name, fake_case_id, synthetic_txn, event_type="CASE_CREATED")

        print("\nDone. Run `python -m scripts.test_cognee` or the live demo's contextual-follow-up "
              "scenario to verify retrieval.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
