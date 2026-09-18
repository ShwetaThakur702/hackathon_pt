# Demo script (~4-5 minutes)

Matches spec section 58. Run `POST /api/simulate/reset` (or click **Reset
Demo** in the UI) before starting.

## Setup

1. Backend running at `http://localhost:8000`, frontend at
   `http://localhost:3000`.
2. Open `http://localhost:3000/` (customer view) in one tab and
   `http://localhost:3000/operations` in another.
3. If demonstrating Cognee memory specifically (Part 3 below), have real
   `COGNEE_API_KEY`/`COGNEE_BASE_URL` configured and optionally run
   `python -m scripts.seed_cognee` beforehand — see "Cognee Memory" in the
   root README. Everything else in this script works identically with
   Cognee unconfigured (`semantic_memory_hits` will just read 0).

## Part 1 — Complaint (customer view)

Select **Priya Sharma (CUST001)** and send:

> Mere ₹2,400 kat gaye but payment fail dikha raha hai.

Point out live, in order:

- The reply cites an exact amount and date pulled from verified system
  state, not generated from nothing.
- The case status card appears: transaction checked → policy evaluated →
  ticket created → follow-up scheduled, with an **expected refund date**.
- Open `/cases/<case_id>` to show the audit-log-driven timeline recording
  each of those steps individually (`COMPLAINT_RECEIVED`,
  `CONTEXT_RETRIEVED`, `TRANSACTION_VERIFIED`, `RULE_EVALUATED`,
  `TICKET_CREATED`, `FOLLOW_UP_SCHEDULED`, ...).

## Part 2 — Autonomous continuation

Still on the case timeline (or customer view), click **Advance to
Deadline**.

- The clock jumps to the policy deadline.
- New timeline events appear without any further customer input:
  `FOLLOW_UP_EXECUTED` (actor `N8N`) → `TRANSACTION_RECHECKED` →
  `RULE_EVALUATED` (now `is_breached: true`) → `DISPUTE_RAISED` →
  `COMPENSATION_CALCULATED` → `NOTIFICATION_SENT`.
- Say explicitly: *"No one sent another message. The case kept working on
  its own."* This is the answer to "what makes this different from a
  chatbot" (spec section 59).

If n8n Cloud is wired up (see `n8n/README.md`), show the n8n execution log
for the workflow run at this point — the same outcome, with the literal
external workflow engine call visible.

## Part 3 — Context (customer view)

Back in the same Priya conversation, send:

> Abhi tak paise nahi aaye.

- No transaction ID was given. Point out the reply still references the
  correct case — the database's open-case lookup resolves it on its own
  (`TransactionService.find_relevant_transaction`), so this part of the
  demo works identically whether or not Cognee is configured.
- Point out the small **🧠 Previous case found** badge under the reply —
  that's the `context_used` field on the `/chat` response, non-sensitive by
  design (it never shows raw memory content to the customer).
- If Cognee is configured: open `/cases/<case_id>` and scroll to **Memory &
  Context**. Say: *"That badge on the customer side comes from here — this
  case's semantic memory, retrieved from Cognee, not hardcoded."* If you
  ran `seed_cognee`, also point at **Related merchant incidents** —
  other customers' Apollo Medicals issues, surfaced by semantic retrieval
  across cases, not a manual join query.
- (Optional) Briefly show the ambiguous-case behavior: if a customer had
  two open failed transactions, Nishchint would ask which one instead of
  guessing — this is `TransactionService.find_relevant_transaction`'s
  ambiguity handling, not a hardcoded response. This still comes from the
  database, not Cognee — Cognee never decides which transaction a message
  refers to.

## Part 4 — Human escalation

Switch the customer selector to **Arjun Mehta (CUST002)** and send:

> Mere 85000 kat gaye TXN85001 payment fail ho gaya.

- The case is immediately routed to `HUMAN_ESCALATED` — the ₹50,000
  configured threshold, not an LLM judgment call.
- Switch to the **Operations** tab: the case appears under **High
  Priority** with the escalation reason and an AI recommendation. Click
  **Approve** (or **Override** to a specific status) and show the
  `HUMAN_OVERRIDE` event land in the audit trail immediately.

## Closing line

> "Nishchint doesn't just answer — it owns the case until it's resolved or
> safely handed to a human. Cognee gives it persistent semantic memory, our
> database stays the source of truth for transactions and case state, and
> our rules engine stays the sole authority for financial decisions.
> Everything you just saw is a real database record and a real audit event,
> not a scripted animation."

## Optional: security guard (30s, if time allows)

Send: `My OTP is 998877`. Show the warning reply, then point out in the
timeline that a `SENSITIVE_CREDENTIAL_DETECTED` event was recorded — and
that the OTP itself never appears anywhere in the case, the messages table,
or the audit log.
