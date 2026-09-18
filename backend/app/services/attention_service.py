"""AttentionService — computes what Nishchint should proactively surface
for a customer (spec sections 8/30-31). Deliberately NOT a stored table:
every call recomputes from current DB state (open cases, bill/FASTag/
AutoPay/refund mismatches), so it can never go stale or duplicate — the
same "derive, don't cache" discipline as the rest of the app's read paths.
"""

from sqlalchemy.orm import Session

from app.models.case import Case
from app.services.autopay_service import autopay_service
from app.services.bill_service import bill_service
from app.services.fastag_service import fastag_service
from app.services.refund_service import refund_service
from app.services.transaction_service import transaction_service


def get_attention_items(db: Session, customer_id: str) -> list[dict]:
    items: list[dict] = []

    open_cases = (
        db.query(Case)
        .filter(Case.customer_id == customer_id, Case.status != "RESOLVED")
        .order_by(Case.created_at.desc())
        .all()
    )
    for case in open_cases:
        txn = transaction_service.get_transaction(db, case.transaction_id) if case.transaction_id else None
        items.append(
            {
                "type": "CASE",
                "id": case.id,
                "title": f"₹{txn['amount']:.0f} · {txn.get('merchant_name') or 'Payment'}" if txn else f"Case {case.id}",
                "subtitle": case.status.replace("_", " ").title(),
                "amount": txn["amount"] if txn else None,
                "cta_label": "View",
                "cta_href": f"/cases/{case.id}",
            }
        )

    for bill in bill_service.get_customer_bills(db, customer_id):
        if bill["nishchint_insight"]["has_issue"]:
            items.append(
                {
                    "type": "BILL",
                    "id": bill["id"],
                    "title": f"₹{bill['amount']:.0f} · {bill['provider_name']}",
                    "subtitle": bill["nishchint_insight"]["message"],
                    "amount": bill["amount"],
                    "cta_label": "Investigate",
                    "cta_href": f"/bills?highlight={bill['id']}",
                }
            )

    fastag = fastag_service.get_account(db, customer_id)
    if fastag and fastag["nishchint_insight"]["has_issue"]:
        items.append(
            {
                "type": "FASTAG",
                "id": fastag["id"],
                "title": f"₹{fastag['last_recharge_amount']:.0f} · FASTag recharge",
                "subtitle": fastag["nishchint_insight"]["message"],
                "amount": fastag["last_recharge_amount"],
                "cta_label": "Review",
                "cta_href": "/fastag",
            }
        )

    for mandate in autopay_service.get_customer_mandates(db, customer_id):
        if mandate["nishchint_insight"]["has_issue"]:
            items.append(
                {
                    "type": "AUTOPAY",
                    "id": mandate["id"],
                    "title": f"₹{mandate['amount']:.0f} · {mandate['biller_name']} AutoPay",
                    "subtitle": mandate["nishchint_insight"]["message"],
                    "amount": mandate["amount"],
                    "cta_label": "Review AutoPay",
                    "cta_href": "/autopay",
                }
            )

    for refund in refund_service.get_customer_refunds(db, customer_id):
        if refund["nishchint_insight"]["has_issue"]:
            items.append(
                {
                    "type": "REFUND",
                    "id": refund["id"],
                    "title": f"₹{refund['amount']:.0f} · {refund['merchant_name']} refund",
                    "subtitle": refund["nishchint_insight"]["message"],
                    "amount": refund["amount"],
                    "cta_label": "Investigate Refund",
                    "cta_href": "/refunds",
                }
            )

    return items
