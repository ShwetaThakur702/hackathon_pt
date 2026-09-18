# Nishchint

**Your autonomous payment & service resolution assistant.**

> Don't chase support. Nishchint investigates, acts, follows up and keeps
> you informed.

Built for the Paytm Build for India AI Hackathon (Bengaluru), Track 3 —
Autonomous AI Teammates. Full product/implementation spec:
[`NISHCHINT_PROTOTYPE_SPEC.md`](./NISHCHINT_PROTOTYPE_SPEC.md).

This is a working vertical slice of a fintech platform, not the full Paytm
product: real frontend (an original Paytm-inspired shell — Home, Payments,
Bills, FASTag, AutoPay, Refunds, Cases), real backend, real database, real
LLM-driven understanding, real LangGraph agent orchestration, a real
deterministic policy engine, a real Cognee semantic-memory layer, a real n8n
follow-up workflow, and a real audit trail — with Paytm/NPCI integrations
represented by clearly isolated mock services (see `docs/architecture.md`).
Nishchint itself is a persistent contextual assistant available from every
page, not a standalone chatbot screen.

## What it demonstrates

**Primary flow — payment exception.** A customer reports a failed UPI
merchant payment once. Nishchint understands it, retrieves context,
verifies the transaction, applies a deterministic refund-deadline policy,
opens a case, and schedules a follow-up — then **keeps working after the
conversation ends**: n8n wakes the case back up at the deadline, the backend
rechecks the transaction, and if the refund is still pending it raises a
dispute, calculates compensation, updates the case, and notifies the
customer, with every step recorded in an audit trail. High-value or
ambiguous cases are routed to a human operations dashboard instead.

**Secondary flows**, demonstrating the same loop applies beyond one failed
payment: an **AutoPay** mandate still scheduled after the bill was already
paid manually (`/autopay`), and a **Bill** payment the provider hasn't
acknowledged yet (`/bills`) — both proactively surfaced on the home
dashboard's "Nishchint is watching N things for you" panel
(`GET /api/nishchint/attention`), not just reachable by asking. **FASTag**
and **Refunds** get the same treatment.

See `docs/demo-script.md` for the full walkthrough.

## Architecture at a glance

```
Next.js  →  FastAPI  →  LangGraph agent  →  Rules engine (deterministic policy)
                              │                    │
                              ▼                    ▼
                       Service layer  ──────  SQLite (system of record)
                          │       │
                          ▼       ▼
                      Cognee   n8n  ──  scheduled follow-up / recheck / dispute
                    (semantic
                     memory,
                     context only)
```

Full breakdown: [`docs/architecture.md`](./docs/architecture.md).
API reference: [`docs/api.md`](./docs/api.md).

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) an Anthropic API key for real LLM understanding/responses —
  the app runs in a deterministic fallback mode without one, see
  [Running without an LLM key](#running-without-an-llm-key).
- (Optional) an n8n Cloud account — see [`n8n/README.md`](./n8n/README.md).
  The autonomous loop is fully demonstrable without it.
- (Optional) a Cognee Cloud account — see
  [Cognee Memory](#cognee-memory) below. The app runs identically without
  it, just without long-term semantic memory.

### 1. Environment variables

```bash
cp .env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Edit `backend/.env` and set `LLM_API_KEY` if you have one. All variables
are documented inline in `.env.example`.

### 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The database (SQLite, `backend/nishchint.db`) and seed data (spec section
23-24: Priya/CUST001, Arjun/CUST002, Rahul/CUST003 and their transactions)
are created automatically on first startup. API docs: `http://localhost:8000/docs`.

Run the test suite (policy, context resolution, safety, escalation, case
state machine, follow-up lifecycle, API integration, Cognee memory — spec
section 42 plus the Cognee integration's own acceptance criteria; Cognee
tests mock the HTTP layer, no real credentials needed):

```bash
python -m pytest
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` — the customer fintech home dashboard, with
`/payments`, `/bills`, `/fastag`, `/autopay`, `/refunds`, `/cases`,
`/transactions/[id]`, `/notifications`, `/profile`, `/travel`, `/rewards`,
and `/customer` (the full-page Nishchint conversation) alongside it. The
floating Nishchint launcher (bottom-right) is available from every one of
those pages. `http://localhost:3000/operations` is the separate internal
human-oversight console — deliberately not part of the customer shell.

### 4. n8n (optional but recommended)

See [`n8n/README.md`](./n8n/README.md) for importing
`n8n/workflows/nishchint-followup-workflow.json` into n8n Cloud and wiring
`N8N_WEBHOOK_URL`. Without it, the demo clock's advance endpoints run the
exact same recheck/decide/act logic directly, so the full loop still works.

### Docker (optional)

```bash
docker compose up --build
```

Starts backend on `:8000` and frontend on `:3000`. n8n still needs to be set
up separately (Cloud, or add your own n8n service to
`docker-compose.yml`) — kept out of the default compose file so Docker
complexity doesn't get in the way of the core build (spec section 70).

## Demo data

Reset any time via the **Reset Demo** button in the UI or `POST
/api/simulate/reset`:

| Customer | ID | Transaction | Amount | Scenario |
|---|---|---|---|---|
| Priya Sharma | CUST001 | TXN24001 | ₹2,400 | Primary demo: merchant payment, T+5 |
| Arjun Mehta | CUST002 | TXN85001 | ₹85,000 | High-value → human escalation |
| Priya Sharma | CUST001 | TXN12001 | ₹1,200 | Already successful (control case) |
| Rahul Verma | CUST003 | TXN30001 | ₹3,000 | P2P payment, T+1 |

Priya (CUST001) additionally has: one Swiggy transaction and two normal
bills (nothing wrong — spec section 29's "don't make everything broken");
one Electricity bill paid but not yet provider-acknowledged; a FASTag
recharge stuck at "balance update pending"; an AutoPay mandate for a bill
she already paid manually (duplicate-risk demo); and an Apollo Medicals
refund the merchant marked complete that she hasn't received. Exact fixtures:
`backend/app/database/seed.py`.

## Running without an LLM key

`LLMService` (`backend/app/integrations/llm`) falls back to a deterministic
regex-based extractor and bilingual response templates when `LLM_API_KEY`
is unset or a call fails — this is the same graceful-degradation path spec
section 43 requires for LLM failures generally, not a shortcut around it.
The core loop (context resolution, policy, case state, follow-ups, audit,
escalation, security guard) works identically either way; what a real LLM
key adds is more natural language understanding of free-form Hindi/Hinglish
phrasing and less template-y responses.

## Cognee Memory

Nishchint uses [Cognee](https://cognee.ai) Cloud as a semantic/long-term
memory layer on top of the application database, funded by the hackathon's
HACKBRIVEN credit at [platform.cognee.ai/billing](https://platform.cognee.ai/billing).

**Why:** the database already tells the agent *what is currently true*
(transaction status, case status, deadlines). Cognee tells it *what has
happened before* — "Priya previously reported this failed payment and was
told the refund date," "three customers have had failed payments at this
merchant" — so a follow-up message like "Abhi tak paise nahi aaye" gets a
reply grounded in the actual prior conversation, and an operator reviewing
a case can see related history at a glance.

**What goes into Cognee:** paraphrased, already-verified narrative text
only — case created, dispute raised, human override, case resolved, and
follow-up recheck outcomes, plus a note after each customer message. Built
by `app/integrations/cognee/memory_formatters.py` from structured fields
(never a raw message, an ORM row, or a credential — see
`docs/architecture.md` "Memory: Cognee" for why that's a structural
guarantee, not a redaction step).

**What never goes into Cognee, and what Cognee never decides:** transaction
status, refund status, deadlines, compensation, dispute status, or any case
state transition. Those come only from `PolicyEngine` and the database, both
before and after this integration — Cognee's retrieval results are labeled
"context only, NOT authoritative" wherever they reach the LLM's prompt, and
`decide_next_action` never reads them at all.

**Configure it:**

```bash
# In backend/.env
COGNEE_ENABLED=true
COGNEE_API_KEY=<from platform.cognee.ai after redeeming HACKBRIVEN>
COGNEE_BASE_URL=https://<your-tenant>.aws.cognee.ai
COGNEE_DATASET=nishchint_memory
```

Leaving `COGNEE_API_KEY` or `COGNEE_BASE_URL` blank (the default) runs the
app with Cognee fully disabled — every other part of Nishchint, including
the "Abhi tak paise nahi aaye" contextual follow-up, works identically via
the database alone.

**Seed, verify, and reset** (run from `backend/`, after `source
.venv/bin/activate`):

```bash
python -m scripts.test_cognee        # verifies real credentials write + retrieve end to end
python -m scripts.seed_cognee        # seeds Priya's history + related-incident demo data
python -m scripts.reset_cognee_demo --yes   # deletes only the nishchint_memory dataset
```

**Verification status:** confirmed working end to end against a real Cognee
Cloud account on 2026-09-18 — `scripts/test_cognee.py` wrote and retrieved
a real memory, and a live `/chat` conversation showed real
`semantic_memory_hits` in `context_used`. Getting there required fixing two
real disagreements between the published docs and the live API (both now
reflected in code and covered by the mocked unit tests, which assert the
corrected shapes):
`POST /api/v1/remember` takes **form-encoded** data, not JSON, and
`raw_data` is a single string, not a list — a JSON body gets a misleading
"Either datasetId or datasetName must be provided" 400 even with
`datasetName` present. `POST /api/v1/search`'s response is a bare JSON
array of `{dataset_id, dataset_name, dataset_tenant_id, search_result:
[str, ...]}`, not `{"results": [{"text": ...}], "status": "success"}` as
documented. See `app/integrations/cognee/cognee_memory_service.py`'s
module docstring for the full detail.

## Known limitations

- External Paytm/NPCI/RBI systems are mocked; no real money moves and no
  real dispute is filed anywhere (spec section 2).
- The policy configuration (`backend/app/rules/policies.json`) is a
  prototype representation of the rules in the original hackathon concept,
  not a legal/compliance-verified source (spec section 10).
- `next@14.2.35` still carries one upstream advisory
  (GHSA-2xp9-vwfh-vxw4, Image Optimization API) whose only full fix is a
  Next 15/16 upgrade; this app doesn't use `next/image`, so the vector isn't
  exercised, but it's untouched here to avoid destabilizing the build during
  the hackathon window.
- Voice input uses local, multilingual speech-to-text via `faster-whisper`
  (`app/integrations/whisper`, `POST /api/voice/transcribe`) — no external
  API key, works offline once the model is cached. Swapped in for the
  originally-planned Sarvam integration for broader language coverage.
  **Verified working end-to-end on 2026-09-18**: real spoken-audio clip in
  → model downloaded live from Hugging Face on first use → correct
  transcription with punctuation and auto-detected language, ~3s per
  request once the model is warm. Still P1 per spec section 48/56: the app
  must not (and does not) depend on it to function — transcription
  failures just mean typing instead. The mic button is on both the
  dedicated `/customer` chat page and the floating assistant launcher.
- LLM provider is Groq (`qwen/qwen3.8-27b`) as of 2026-09-19, switched
  from Gemini after Google started rate-limiting that key. Groq itself is
  fast (sub-30ms completions, verified live) — per-turn `/chat` latency
  (~15-20s) is actually dominated by Cognee Cloud's `/remember`+`/search`
  round trips (2-3 real network calls per turn), not the LLM. Both
  Anthropic and Gemini provider code remain in place (`LLM_PROVIDER=
  anthropic|gemini|groq`) if you want to switch back.
- Cognee memory and n8n Cloud are both verified working against real
  accounts — see [Cognee Memory](#cognee-memory) above. The one real gap:
  n8n Cloud cannot call back into a backend running on `localhost` (SSRF
  protection actively blocks it, confirmed via a real execution log) — see
  `n8n/README.md` for the ngrok/deployment fix. The demo works fully
  either way via the simulated-clock fallback.
- Fraud detection is a small keyword heuristic in `agent/nodes.py`, not the
  full fraud engine explicitly marked out of scope (spec section 5.3).
- The fintech shell (Home/Payments/Bills/FASTag/AutoPay/Refunds/Cases) was
  verified via `tsc`, a full production build, and live API/route smoke
  tests (all 16 routes return 200, zero console/build errors) — not via
  visual screenshots at every breakpoint, since no browser/screenshot tool
  is available in this environment. Layouts use Tailwind's mobile-first
  responsive classes throughout, but haven't been eyeballed pixel-by-pixel
  at all nine target widths from spec section 7.
- Bills/FASTag/AutoPay/Refunds are intentionally light (spec section 20):
  real backend models, endpoints, and deterministic insights, but no
  workflow depth beyond investigate/review/cancel — Travel/Rewards are
  static mock pages with no backend, also per section 20.
- Global search (`SearchModal`) is a client-side filter over the current
  customer's already-fetched transactions/cases, not a dedicated backend
  search endpoint — adequate for the demo dataset's size, not built to
  scale to a real transaction history.
