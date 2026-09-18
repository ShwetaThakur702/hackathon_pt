# n8n — Nishchint follow-up automation

n8n owns the asynchronous half of the core loop: once the agent schedules a
follow-up during `/chat`, n8n is what wakes the workflow back up later,
rechecks the transaction, and drives it to resolution/dispute/escalation
without the customer being in the conversation. See architectural Rule 5 and
section 52 of `NISHCHINT_PROTOTYPE_SPEC.md` for why this is a separate layer
from the LangGraph agent and the rules engine.

## What the workflow does

`workflows/nishchint-followup-workflow.json` implements spec section 20.1:

```
Webhook (follow-up scheduled)
  -> Validate payload
  -> Wait until scheduled_for (the policy deadline)
  -> POST /api/workflows/execute-followup   (backend re-checks the
     transaction, re-evaluates the policy, and resolves/disputes/escalates —
     this is where the actual decision logic lives, not in n8n)
  -> POST /api/workflows/followup-result    (reports the outcome back for
     audit — matches the callback contract in spec section 51; safe to call
     even though the backend already updated state, because that endpoint is
     idempotent)
```

The recheck → policy → decide → act logic intentionally lives in the backend
(`FollowupService.execute_due_followup`), not inside n8n nodes. n8n's job is
orchestration/timing (spec section 52: "Do not put the entire AI brain
inside n8n"); the backend's rules engine remains the single source of truth
for financial decisions.

## Setup (n8n Cloud)

**Automated (recommended):** with `N8N_BASE_URL` and `N8N_API_KEY` set in
`backend/.env` (get these from n8n Cloud → Settings → API), run:

```bash
cd backend && source .venv/bin/activate
python -m scripts.setup_n8n_workflow
```

This creates/updates and activates the workflow via n8n's Management REST
API, inlining your actual `BACKEND_BASE_URL`/`N8N_CALLBACK_SECRET` directly
into the two HTTP Request nodes (n8n Cloud doesn't offer a simple UI for
setting custom instance environment variables, so the portable JSON
template's `$env.BACKEND_BASE_URL`/`$env.N8N_CALLBACK_SECRET` expressions
are only meant for manual-import setups — see "Manual" below). It prints
the production webhook URL — copy that into `N8N_WEBHOOK_URL` in
`backend/.env`, restart the backend, then run
`python -m scripts.test_n8n` to confirm the round trip.

**Verified 2026-09-18** against a real n8n Cloud account: authentication,
workflow creation, activation, and the webhook trigger all confirmed
working (execution log showed the run passing through the Webhook → Validate
→ Wait nodes correctly). The one real constraint, also confirmed via a live
execution error: **n8n Cloud actively blocks requests to `localhost`/
`127.0.0.1`** as SSRF protection — so if `BACKEND_BASE_URL` points at your
local machine, the workflow's callback to your backend will fail at the
"Execute Follow-up" node specifically (everything before it still runs
correctly). Fix with a public tunnel:

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

## Manually triggering the webhook for testing

```bash
curl -X POST "$N8N_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "CASE-1042",
    "customer_id": "CUST001",
    "transaction_id": "TXN24001",
    "followup_id": "FUP-ABC123",
    "scheduled_for": "2026-09-15T09:00:00",
    "action": "RECHECK_FAILED_PAYMENT"
  }'
```
