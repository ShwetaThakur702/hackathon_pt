# n8n — Nishchint follow-up automation

n8n owns the asynchronous half of the core loop: once the agent schedules a
follow-up during `/chat`, n8n is what wakes the workflow back up later,
rechecks the transaction, and drives it to resolution/dispute/escalation
without the customer being in the conversation. See architectural Rule 5 and
section 52 of `NISHCHINT_PROTOTYPE_SPEC.md` for why this is a separate layer
from the LangGraph agent and the rules engine.

## What the workflow does

`workflows/nishchint-followup-workflow.json` implements spec section 20.1,
upgraded to branch explicitly on outcome instead of a single straight line:

```
Webhook: Follow-up Scheduled  (responseMode=onReceived — acknowledges instantly,
                                never makes the scheduling caller wait on Wait/Execute)
  -> Validate & Normalize Payload   (event_id/followup_id, case_id, customer_id,
                                      next_check_at all present; upi_reference_id
                                      numeric if included — no business-deadline math)
  -> Wait - Next Check              (waits until the backend-supplied timestamp —
                                      never a hardcoded delay, never computed here)
  -> Execute Follow-up - Backend    (POST /api/workflows/execute-followup — the
                                      ONLY place a decision is made: backend rechecks
                                      the transaction, re-evaluates the policy engine,
                                      and performs the action. Idempotent per
                                      followup_id/event_id, retried up to 3x on failure)
  -> Switch - Follow-up Outcome     (branches on the backend's own `outcome` field)
     |
     +-- RESOLVED             -> Report Result -> Notify Customer -> Memory Recorded
     +-- DISPUTE_RAISED /
     |   ESCALATED             -> Report Result -> Notify Customer -> Memory Recorded
     +-- CONTINUE_MONITORING  -> Report Result -> (ends — see below)
```

The recheck → policy → decide → act logic intentionally lives in the backend
(`FollowupService.execute_due_followup`), not inside n8n nodes. n8n's job is
orchestration/timing/branching/notification (spec section 52: "Do not put the
entire AI brain inside n8n"); the backend's rules engine remains the single
source of truth for financial decisions — `current_compensation` in every
branch is the exact value `/execute-followup` returned, never recomputed by
n8n.

**"Switch - Follow-up Outcome"** is implemented as two chained IF nodes
(`Switch - Resolved?` then `Switch - Action Taken or Escalated?`) rather than
a single Switch node — both IF nodes reuse the exact same node type/schema as
the already-verified-working `Validate & Normalize Payload`, which is lower
risk than a more complex node type for a workflow you may need to hand-edit.

**"Report Result - Backend"** and **"Notify Customer"** are real HTTP calls,
not decorative nodes — but every value they send (`outcome`,
`current_compensation`, `notification_message`, ...) is read straight off
`Execute Follow-up - Backend`'s own response via `$('Execute Follow-up -
Backend').item.json...`, never recomputed. `Notify Customer` is safe to
retry/replay: the backend's notification service dedupes on an exact
`(customer_id, case_id, message)` match, and the message text it sends is the
literal one `/execute-followup` already generated and sent — so this call
can never produce a second, differently-worded notification.

**"Memory Recorded"** nodes are intentionally `NoOp` — the backend's
`MemoryService` already wrote the resolution event to Cognee synchronously
inside `/execute-followup`. A second, independent n8n → Cognee write would
duplicate memory logic (spec section 15 explicitly prefers this simpler
architecture); the NoOp node just keeps the requested branch shape visible
in the canvas, with a note explaining why it does nothing.

### How the autonomous loop continues (CONTINUE_MONITORING / DISPUTE_RAISED)

The CONTINUE_MONITORING branch does **not** loop back to `Wait - Next Check`
inside the same execution. Instead: `FollowupService.execute_due_followup`
(and the DISPUTE_RAISED branch, which also reschedules a next-day recheck so
the compensation keeps accruing) calls `FollowupService.schedule()` for the
next check — and `schedule()` itself fires a **brand-new** "Follow-up
Scheduled" webhook call to n8n, starting a fresh, independent workflow
execution with its own new `event_id`. This is simpler and safer than an
in-workflow cycle: each execution's idempotency key is unambiguous, there's
no risk of a stale `followup_id` being reused across loop iterations, and
the workflow itself stays a straight-line DAG instead of a cyclic graph.

## Setup (n8n Cloud)

**Automated (recommended):** with `N8N_BASE_URL` and `N8N_API_KEY` set in
`backend/.env` (get these from n8n Cloud → Settings → API), run:

```bash
cd backend && source .venv/bin/activate
python -m scripts.setup_n8n_workflow
```

This creates/updates and activates the workflow via n8n's Management REST
API, inlining your actual `BACKEND_BASE_URL` and a real `N8N_CALLBACK_SECRET`
directly into every HTTP Request node's URL, JSON body, and `Authorization:
Bearer` header (n8n Cloud doesn't offer a simple UI for setting custom
instance environment variables, so the portable JSON template's
`$env.BACKEND_BASE_URL`/`$env.N8N_CALLBACK_SECRET` expressions are only
meant for manual-import setups — see "Manual" below). It prints the
production webhook URL — copy that into `N8N_WEBHOOK_URL` in `backend/.env`,
restart the backend, then run `python -m scripts.test_n8n` to confirm the
round trip.

**The script now refuses to deploy if `BACKEND_BASE_URL` points at
`localhost`/`127.0.0.1`/`0.0.0.0`** — it fails loudly instead of silently
inlining a URL n8n Cloud can never reach (this is exactly what happened
before this guard existed: a real n8n Cloud workflow ended up with
`http://localhost:8000` baked into its HTTP Request nodes). Pass
`--allow-localhost` only if n8n itself is self-hosted on this same
machine/network. It also auto-generates and persists a real
`N8N_CALLBACK_SECRET` into `backend/.env` if it's still unset or the
insecure default `change-me` — never deploys that default to a real webhook.

**Verified 2026-09-18** against a real n8n Cloud account: authentication,
workflow creation, activation, and the webhook trigger all confirmed
working (execution log showed the run passing through the Webhook → Validate
→ Wait nodes correctly). The one real constraint, also confirmed via a live
execution error: **n8n Cloud actively blocks requests to `localhost`/
`127.0.0.1`** as SSRF protection — so if `BACKEND_BASE_URL` points at your
local machine, the workflow's callback to your backend will fail at the
"Execute Follow-up" node specifically (everything before it still runs
correctly; the setup script's localhost guard above now catches this before
deploying, rather than after). Fix with a public tunnel:

```bash
brew install ngrok   # or download from ngrok.com
ngrok http 8000
# copy the https://*.ngrok-free.app URL it prints
```

Then set `BACKEND_BASE_URL=https://<that>.ngrok-free.app` in
`backend/.env`, restart the backend, and re-run
`python -m scripts.setup_n8n_workflow` to repoint the workflow at it.

**Manual (alternative):**

1. Create an n8n Cloud workspace (or self-hosted instance).
2. **Workflow → Import from File** and select
   `workflows/nishchint-followup-workflow.json`.
3. Set these Environment Variables on the n8n instance (Settings →
   Environment Variables, or Cloud workspace variables — self-hosted only;
   n8n Cloud's standard plan does not expose this):
   - `BACKEND_BASE_URL` — the publicly reachable URL of the FastAPI backend
     (e.g. an ngrok tunnel to `localhost:8000` for a local demo, or your
     deployed backend URL).
   - `N8N_CALLBACK_SECRET` — must match `N8N_CALLBACK_SECRET` in the
     backend's `.env`.
4. Activate the workflow. Copy its **Webhook: Follow-up Scheduled** node's
   production URL.
5. Set that URL as `N8N_WEBHOOK_URL` in the backend's `.env` and restart the
   backend.

## Running the demo without n8n Cloud configured

`N8N_WEBHOOK_URL` is optional. If it's empty, `N8nClient` logs the attempted
call and no-ops instead of failing (spec section 73: never assume an
external service is available). The backend's `POST
/api/simulate/advance-time` / `advance-to-deadline` endpoints directly call
the same `execute_due_followup` logic that the n8n workflow would trigger, so
the full autonomous loop (recheck → dispute → compensation → notify → audit)
is fully demonstrable with just the backend running. This is not a fake
follow-up — it's the identical deterministic backend logic; only the
"what wakes it up" transport differs. Wiring up real n8n Cloud on top of that
adds the literal "external workflow engine calls us back" hop for judges who
want to see it, without changing any of the decision logic.

## Endpoints this workflow calls

| Endpoint | Called by | Purpose |
| --- | --- | --- |
| `POST /api/workflows/execute-followup` | `Execute Follow-up - Backend` | The only decision point — recheck, policy, act. Idempotent per `followup_id`/`event_id`. |
| `POST /api/workflows/notify-customer` | `Notify Customer (*)` | Persists the customer notification. Requires `Authorization: Bearer <N8N_CALLBACK_SECRET>` (or legacy `secret` body field). Dedup'd on exact `(customer_id, case_id, message)`. |
| `POST /api/workflows/followup-result` | `Report Result - Backend (*)` | Audit-only — records that n8n saw this outcome. Never transitions the case itself (that already happened inside `/execute-followup`); same auth as above. |

## Manually triggering the webhook for testing

```bash
curl -X POST "$N8N_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "FUP-ABC123",
    "followup_id": "FUP-ABC123",
    "case_id": "CASE-1042",
    "customer_id": "CUST-001",
    "correlation_id": "CASE-1042",
    "transaction_id": "TXN24001",
    "upi_reference_id": "624718395021",
    "scheduled_for": "2026-09-15T09:00:00",
    "next_check_at": "2026-09-15T09:00:00",
    "reason": "RECHECK_FAILED_PAYMENT",
    "action": "RECHECK_FAILED_PAYMENT"
  }'
```
