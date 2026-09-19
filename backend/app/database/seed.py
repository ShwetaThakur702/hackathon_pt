"""Seed / reset demo data (spec sections 23-24, 28).

`reset_and_seed` is what POST /simulate/reset calls, and what runs once at
app startup if the database is empty — the demo must never require manually
editing database records (spec section 37).

Every date below is built as an offset from `demo_anchor_date()` (always
the real "today"), not a hardcoded calendar date — so the demo never goes
stale, and every relative relationship (T+5 deadlines, "bill paid before
the AutoPay mandate fires" etc.) stays correct no matter what day it's
reset on. Recomputed inside `reset_and_seed` itself (not module-level
constants) so a long-running process picks up a new day naturally.

Single-customer demo (spec: "Single customer experience"): exactly ONE
customer is seeded — CUST-001 / Priya Sharma. All transactions, bills,
FASTag, AutoPay, refunds and cases below belong to her; there is no
customer switcher in the product anymore (see frontend/lib/customer-
context.tsx). Most of her activity is normal (spec: "do not make every
transaction problematic") — only a deliberate few items carry an
exception, so the proactive attention list stays believable rather than
alarming.
"""

from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.autopay_mandate import AutoPayMandate
from app.models.bill import Bill
from app.models.case import Case
from app.models.customer import Customer
from app.models.dispute import Dispute
from app.models.fastag_account import FastagAccount
from app.models.followup import Followup
from app.models.message import Message
from app.models.notification import Notification
from app.models.refund import Refund
from app.models.sim_clock import SimClock
from app.models.transaction import Transaction
from app.services.simulation_clock import demo_anchor_date, demo_start

CUSTOMER_ID = "CUST-001"

CUSTOMERS = [
    Customer(id=CUSTOMER_ID, name="Priya Sharma", phone="9800000001", preferred_language="Hindi"),
]

ALL_MODELS_TO_CLEAR = [
    Notification, AuditLog, Message, Dispute, Followup, Case,
    AutoPayMandate, Refund, Bill, FastagAccount, Transaction, Customer, SimClock,
]


def _build_transactions(today):
    """Priya's transaction ledger (spec section 6) — one raw `Transaction`
    row per demo incident, each with a real-looking 12-digit numeric UPI
    Reference ID as the customer-facing identifier (internal `id` is never
    shown in the UI; see Transaction.upi_ref_no). Most of it is normal
    activity (#2, #3) — the rest each back one of the five incidents in
    the Bills/FASTag/AutoPay/Refunds pages (see _build_bills /
    FASTAG_ACCOUNTS / _build_autopay_mandates / REFUNDS below), plus one
    high-value transaction (#8) that exists purely to demo the
    HIGH_VALUE_TRANSACTION human-escalation path."""
    return [
        # 1. Apollo Medicals — failed payment, amount debited, refund
        # pending. The primary autonomous-resolution demo.
        Transaction(
            id="TXN24001", upi_ref_no="624718395021", customer_id=CUSTOMER_ID, amount=2400, currency="INR",
            type="MERCHANT", merchant_name="Apollo Medicals", status="FAILED", debited=True, merchant_credited=False,
            refund_status="PENDING", transaction_date=today,
        ),
        # 2. Swiggy — normal, completed.
        Transaction(
            id="TXN00850", upi_ref_no="731928465019", customer_id=CUSTOMER_ID, amount=850, currency="INR",
            type="MERCHANT", merchant_name="Swiggy", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today - timedelta(days=2),
        ),
        # 3. Electricity — normal, completed (distinct from #4's exception).
        Transaction(
            id="TXN12001", upi_ref_no="845716239004", customer_id=CUSTOMER_ID, amount=1200, currency="INR",
            type="MERCHANT", merchant_name="Electricity", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today - timedelta(days=1),
        ),
        # 4. Electricity Board — payment successful, provider hasn't acked
        # it yet. Backs BILL-ELEC-001 below.
        Transaction(
            id="TXN38401", upi_ref_no="592814637201", customer_id=CUSTOMER_ID, amount=3840, currency="INR",
            type="MERCHANT", merchant_name="Electricity Board", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today - timedelta(days=1),
        ),
        # 5. FASTag recharge — payment successful, balance update pending.
        # Backs FASTAG-CUST-001 below.
        Transaction(
            id="TXN10001", upi_ref_no="619482753016", customer_id=CUSTOMER_ID, amount=1000, currency="INR",
            type="MERCHANT", merchant_name="FASTag Recharge", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today,
        ),
        # 6. HDFC Credit Card — manual payment successful, AutoPay still
        # scheduled (duplicate-debit risk). Backs BILL-CC-001/AUTOPAY-CC-001.
        Transaction(
            id="TXN50001", upi_ref_no="785213649027", customer_id=CUSTOMER_ID, amount=5000, currency="INR",
            type="MERCHANT", merchant_name="HDFC Credit Card", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today + timedelta(days=8),
        ),
        # 7. Apollo Medicals refund — merchant marked it completed, customer
        # hasn't received it. Backs REFUND-APOLLO-001 below.
        Transaction(
            id="TXN28001", upi_ref_no="913647285104", customer_id=CUSTOMER_ID, amount=2800, currency="INR",
            type="MERCHANT", merchant_name="Apollo Medicals", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="PENDING", transaction_date=today - timedelta(days=3),
        ),
        # 8. High-value transaction — exists solely to demo the
        # HIGH_VALUE_TRANSACTION human-escalation path (>= policy threshold).
        Transaction(
            id="TXN85001", upi_ref_no="402917568321", customer_id=CUSTOMER_ID, amount=85000, currency="INR",
            type="MERCHANT", merchant_name="Demo Electronics", status="FAILED", debited=True, merchant_credited=False,
            refund_status="PENDING", transaction_date=today,
        ),
    ]


def _build_bills(today):
    return [
        Bill(
            id="BILL-ELEC-001", customer_id=CUSTOMER_ID, category="ELECTRICITY", provider_name="City Electricity Board",
            amount=3840, status="PAID", provider_ack_status="PENDING",
            due_date=today + timedelta(days=2), paid_date=today - timedelta(days=1),
        ),
        Bill(
            id="BILL-MOBILE-001", customer_id=CUSTOMER_ID, category="MOBILE", provider_name="Airtel",
            amount=399, status="PAID", provider_ack_status="ACKNOWLEDGED",
            due_date=today - timedelta(days=5), paid_date=today - timedelta(days=6),
        ),
        Bill(
            id="BILL-DTH-001", customer_id=CUSTOMER_ID, category="DTH", provider_name="Tata Play",
            amount=450, status="PAID", provider_ack_status="ACKNOWLEDGED",
            due_date=today - timedelta(days=7), paid_date=today - timedelta(days=8),
        ),
        # Paid manually ahead of the AutoPay mandate below — the section 18/59 duplicate-risk demo.
        Bill(
            id="BILL-CC-001", customer_id=CUSTOMER_ID, category="LOAN", provider_name="HDFC Credit Card",
            amount=5000, status="PAID", provider_ack_status="ACKNOWLEDGED",
            due_date=today + timedelta(days=15), paid_date=today + timedelta(days=8),
        ),
    ]


def _build_autopay_mandates(today):
    return [
        AutoPayMandate(
            id="AUTOPAY-ELEC-001", customer_id=CUSTOMER_ID, biller_name="City Electricity Board", amount=3840,
            frequency="MONTHLY", next_charge_date=today + timedelta(days=10), status="ACTIVE", linked_bill_id=None,
        ),
        # Duplicate-risk mandate: linked bill already paid manually before this charge date.
        AutoPayMandate(
            id="AUTOPAY-CC-001", customer_id=CUSTOMER_ID, biller_name="HDFC Credit Card", amount=5000,
            frequency="MONTHLY", next_charge_date=today + timedelta(days=15), status="ACTIVE", linked_bill_id="BILL-CC-001",
        ),
    ]


FASTAG_ACCOUNTS = [
    FastagAccount(
        id="FASTAG-CUST-001", customer_id=CUSTOMER_ID, balance=1280,
        last_recharge_amount=1000, last_recharge_status="BALANCE_UPDATE_PENDING",
    ),
]

REFUNDS = [
    Refund(
        id="REFUND-APOLLO-001", customer_id=CUSTOMER_ID, merchant_name="Apollo Medicals", amount=2800,
        original_transaction_id="TXN28001", merchant_status="COMPLETED", customer_received=False,
    ),
]


def _build_notifications(today):
    """Priya's notification history — so /notifications shows real content
    from the first load rather than an empty state (notifications are
    otherwise only generated live, as a case actually progresses). These
    are backdated (created_at in the past relative to `today`), matching a
    customer who's had a working relationship with Nishchint before this
    demo session started — including one closed case, consistent with the
    "previous interaction found" narrative Cognee/MemoryPanel refer to
    elsewhere for CASE-SEED-DEMO/Apollo Medicals."""
    def _at(days_ago: int, hour: int, minute: int) -> datetime:
        d = today - timedelta(days=days_ago)
        return datetime.combine(d, time(hour, minute), tzinfo=timezone.utc)

    return [
        Notification(
            customer_id=CUSTOMER_ID, case_id=None, channel="IN_APP", status="SENT",
            message="मैंने आपकी पिछली Apollo Medicals भुगतान की शिकायत सुलझा दी है। रिफंड सफलतापूर्वक प्राप्त हो चुका है।",
            created_at=_at(7, 11, 20),
        ),
        Notification(
            customer_id=CUSTOMER_ID, case_id=None, channel="IN_APP", status="SENT",
            message="आपका Tata Play DTH रिचार्ज ₹450 सफलतापूर्वक प्रोसेस हो गया है।",
            created_at=_at(3, 9, 5),
        ),
        Notification(
            customer_id=CUSTOMER_ID, case_id=None, channel="IN_APP", status="SENT",
            message="आपका Airtel मोबाइल बिल ₹399 समय पर भुगतान हो गया है, कोई कार्रवाई आवश्यक नहीं।",
            created_at=_at(1, 18, 40),
        ),
    ]


def reset_and_seed(db: Session) -> None:
    for model in ALL_MODELS_TO_CLEAR:
        db.query(model).delete()
    db.commit()

    today = demo_anchor_date()

    for customer in CUSTOMERS:
        db.add(Customer(id=customer.id, name=customer.name, phone=customer.phone, preferred_language=customer.preferred_language))
    for txn in _build_transactions(today):
        db.add(
            Transaction(
                id=txn.id, upi_ref_no=txn.upi_ref_no, customer_id=txn.customer_id, amount=txn.amount, currency=txn.currency,
                type=txn.type, merchant_name=txn.merchant_name, status=txn.status, debited=txn.debited,
                merchant_credited=txn.merchant_credited, refund_status=txn.refund_status,
                transaction_date=txn.transaction_date,
            )
        )
    db.commit()  # bills committed before autopay mandates that reference them via FK

    for bill in _build_bills(today):
        db.add(
            Bill(
                id=bill.id, customer_id=bill.customer_id, category=bill.category, provider_name=bill.provider_name,
                amount=bill.amount, status=bill.status, provider_ack_status=bill.provider_ack_status,
                due_date=bill.due_date, paid_date=bill.paid_date,
            )
        )
    db.commit()

    for account in FASTAG_ACCOUNTS:
        db.add(
            FastagAccount(
                id=account.id, customer_id=account.customer_id, balance=account.balance,
                last_recharge_amount=account.last_recharge_amount, last_recharge_status=account.last_recharge_status,
            )
        )
    for mandate in _build_autopay_mandates(today):
        db.add(
            AutoPayMandate(
                id=mandate.id, customer_id=mandate.customer_id, biller_name=mandate.biller_name, amount=mandate.amount,
                frequency=mandate.frequency, next_charge_date=mandate.next_charge_date, status=mandate.status,
                linked_bill_id=mandate.linked_bill_id,
            )
        )
    for refund in REFUNDS:
        db.add(
            Refund(
                id=refund.id, customer_id=refund.customer_id, merchant_name=refund.merchant_name, amount=refund.amount,
                original_transaction_id=refund.original_transaction_id, merchant_status=refund.merchant_status,
                customer_received=refund.customer_received,
            )
        )
    for notification in _build_notifications(today):
        db.add(
            Notification(
                customer_id=notification.customer_id, case_id=notification.case_id, channel=notification.channel,
                message=notification.message, status=notification.status, created_at=notification.created_at,
            )
        )

    db.add(SimClock(id=1, current_time=demo_start()))
    db.commit()


def seed_if_empty(db: Session) -> None:
    if db.query(Customer).count() == 0:
        reset_and_seed(db)
