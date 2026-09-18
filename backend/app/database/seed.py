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

Most of Priya's activity is normal (spec section 29: "do not make everything
broken") — only a deliberate few items carry an exception, so the proactive
attention list stays believable rather than alarming.
"""

from datetime import timedelta

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

CUSTOMERS = [
    Customer(id="CUST001", name="Priya Sharma", phone="9800000001", preferred_language="Hindi"),
    Customer(id="CUST002", name="Arjun Mehta", phone="9800000002", preferred_language="English"),
    Customer(id="CUST003", name="Rahul Verma", phone="9800000003", preferred_language="Hindi"),
]

ALL_MODELS_TO_CLEAR = [
    Notification, AuditLog, Message, Dispute, Followup, Case,
    AutoPayMandate, Refund, Bill, FastagAccount, Transaction, Customer, SimClock,
]


def _build_transactions(today):
    return [
        Transaction(
            id="TXN24001", upi_ref_no="809489842596", customer_id="CUST001", amount=2400, currency="INR",
            type="MERCHANT", merchant_name="Apollo Medicals", status="FAILED", debited=True, merchant_credited=False,
            refund_status="PENDING", transaction_date=today,
        ),
        Transaction(
            id="TXN85001", upi_ref_no="402917568321", customer_id="CUST002", amount=85000, currency="INR",
            type="MERCHANT", merchant_name="Demo Electronics", status="FAILED", debited=True, merchant_credited=False,
            refund_status="PENDING", transaction_date=today,
        ),
        Transaction(
            id="TXN12001", upi_ref_no="305612894477", customer_id="CUST001", amount=1200, currency="INR",
            type="MERCHANT", merchant_name="Demo Store", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today - timedelta(days=1),
        ),
        Transaction(
            id="TXN00850", upi_ref_no="718293045566", customer_id="CUST001", amount=850, currency="INR",
            type="MERCHANT", merchant_name="Swiggy", status="SUCCESS", debited=True, merchant_credited=True,
            refund_status="NOT_APPLICABLE", transaction_date=today - timedelta(days=2),
        ),
        Transaction(
            id="TXN30001", upi_ref_no="601738492215", customer_id="CUST003", amount=3000, currency="INR",
            type="PERSON", merchant_name=None, status="FAILED", debited=True, merchant_credited=None,
            refund_status="PENDING", transaction_date=today,
        ),
    ]


def _build_bills(today):
    return [
        Bill(
            id="BILL-ELEC-001", customer_id="CUST001", category="ELECTRICITY", provider_name="City Electricity Board",
            amount=3840, status="PAID", provider_ack_status="PENDING",
            due_date=today + timedelta(days=2), paid_date=today - timedelta(days=1),
        ),
        Bill(
            id="BILL-MOBILE-001", customer_id="CUST001", category="MOBILE", provider_name="Airtel",
            amount=399, status="PAID", provider_ack_status="ACKNOWLEDGED",
            due_date=today - timedelta(days=5), paid_date=today - timedelta(days=6),
        ),
        Bill(
            id="BILL-DTH-001", customer_id="CUST001", category="DTH", provider_name="Tata Play",
            amount=450, status="PAID", provider_ack_status="ACKNOWLEDGED",
            due_date=today - timedelta(days=7), paid_date=today - timedelta(days=8),
        ),
        # Paid manually ahead of the AutoPay mandate below — the section 18/59 duplicate-risk demo.
        Bill(
            id="BILL-CC-001", customer_id="CUST001", category="LOAN", provider_name="HDFC Credit Card",
            amount=5000, status="PAID", provider_ack_status="ACKNOWLEDGED",
            due_date=today + timedelta(days=15), paid_date=today + timedelta(days=8),
        ),
    ]


def _build_autopay_mandates(today):
    return [
        AutoPayMandate(
            id="AUTOPAY-ELEC-001", customer_id="CUST001", biller_name="City Electricity Board", amount=3840,
            frequency="MONTHLY", next_charge_date=today + timedelta(days=10), status="ACTIVE", linked_bill_id=None,
        ),
        # Duplicate-risk mandate: linked bill already paid manually before this charge date.
        AutoPayMandate(
            id="AUTOPAY-CC-001", customer_id="CUST001", biller_name="HDFC Credit Card", amount=5000,
            frequency="MONTHLY", next_charge_date=today + timedelta(days=15), status="ACTIVE", linked_bill_id="BILL-CC-001",
        ),
    ]


FASTAG_ACCOUNTS = [
    FastagAccount(
        id="FASTAG-CUST001", customer_id="CUST001", balance=1280,
        last_recharge_amount=1000, last_recharge_status="BALANCE_UPDATE_PENDING",
    ),
]

REFUNDS = [
    Refund(
        id="REFUND-APOLLO-001", customer_id="CUST001", merchant_name="Apollo Medicals", amount=2800,
        original_transaction_id=None, merchant_status="COMPLETED", customer_received=False,
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

    db.add(SimClock(id=1, current_time=demo_start()))
    db.commit()


def seed_if_empty(db: Session) -> None:
    if db.query(Customer).count() == 0:
        reset_and_seed(db)
