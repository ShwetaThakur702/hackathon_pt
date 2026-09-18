# Architecture

Nishchint is a vertical slice of an autonomous AI support teammate for
failed UPI merchant payments. The full spec is
[`NISHCHINT_PROTOTYPE_SPEC.md`](../NISHCHINT_PROTOTYPE_SPEC.md); this
document is a map of how the prototype implements it.

## Core mantra

> LLM understands. Cognee remembers. The database verifies. Rules decide
> policy. Tools act. n8n continues the work. Humans handle risk. Audit
> records everything.

Every architectural decision below exists to keep those sentences true in
code, not just in prose.

## Component diagram

```
Next.js (customer UI, case timeline, operations dashboard)
        │  REST (fetch)
        ▼
FastAPI (backend/app/api/*) ── request/response boundary, Pydantic validation
        │
        ▼
LangGraph agent (backend/app/agent) ── understand → retrieve context (DB + Cognee,
via ContextAssembler) → identify transaction → investigate → evaluate policy →
decide → act → schedule follow-up → audit → respond
        │              │                 │              │
        ▼              ▼                 ▼              ▼
  Rules engine   Service layer      Mock Paytm-style   Cognee Cloud
  (deterministic (case/transaction/  data (SQLite via  (semantic/historical
  policy math)   dispute/followup/   SQLAlchemy)       memory — context only,
                 notification/audit)                   never authoritative)
                       │
                       ▼
                      n8n ── scheduled recheck, calls back into
                             POST /api/workflows/execute-followup
```

`decide_next_action` only ever reads from the rules engine / database
branch of this diagram. Cognee's output can reach `execute_action` only
indirectly, through the phrasing of the LLM's customer-facing reply — never
through the decision itself. See "Memory: Cognee (semantic layer)" below.

## Why each layer exists

- **FastAPI (`app/api`)** — the only HTTP surface. Validates input with
  Pydantic, never touches the ORM directly; everything goes through
  `app/services`.
- **LangGraph agent (`app/agent`)** — a fixed graph (not a free-form ReAct
  loop) mirroring spec section 12.2 exactly: `understand_complaint →
  retrieve_context → identify_transaction → investigate_transaction →
  evaluate_policy → decide_next_action → execute_action →
  schedule_followup → write_audit → generate_response`. Nodes call
  `app/agent/tools.py`, never the ORM (architectural Rule 3). A
  sensitive-credential message short-circuits straight to
  `generate_response` so a PIN/OTP never reaches the LLM, Cognee, or the
  rest of the pipeline — no case exists yet at that point in the graph, so
  there is no code path through which a secret could be written to memory.
  `retrieve_context` calls a single tool, `assemble_context`, which is the
  only place the agent touches memory — it never calls the database and
  Cognee separately itself (spec section 11).
- **LLMService (`app/integrations/llm`)** — the only place a provider SDK is
  imported. Used for two things only: extracting intent/entities from the
  customer's message, and phrasing a customer-facing reply around
  *already-verified* facts it is given. It never computes a deadline,
  amount, or status (architectural Rule 1). If no `LLM_API_KEY` is
  configured or the call fails, a conservative deterministic fallback
  (regex extraction + bilingual templates) keeps the loop working in a
  clearly degraded mode — spec section 43's failure-handling requirement.
- **Rules engine (`app/rules/engine.py`)** — pure, deterministic, no I/O.
  `PolicyEngine.evaluate()` computes deadlines (`T+1`/`T+5` calendar days,
  not business days), breach detection, and per-day compensation from
  `app/rules/policies.json`. This is the only place financial policy math
  happens (architectural Rule 2).
- **Service layer (`app/services`)** — one service per concern
  (`TransactionService`, `CaseService`, `TicketService`, `DisputeService`,
  `FollowupService`, `NotificationService`, `AuditService`,
  `MemoryService`, `ContextAssembler`, `SimulationClockService`,
  `N8nClient`). Mock Paytm-style behavior lives in `TransactionService`; a
  real Paytm adapter would replace only that file.
- **Case state machine (`app/models/case.py` +
  `CaseService.transition`/`advance_to`)** — an explicit `VALID_TRANSITIONS`
  graph. `transition()` enforces single-hop validity and is what the human
  override endpoint uses (an invalid override is rejected with 409).
  `advance_to()` is a BFS-based *forward-progression* helper the agent
  pipeline uses internally — it treats an unreachable target as "already
  past this point" (e.g. a contextual follow-up reusing an already
  in-progress case) rather than an error, while `transition()` stays strict.
- **Audit (`app/services/audit_service.py`)** — every meaningful action
  (Rule 6's list) writes a row here, timestamped with the *simulated* clock.
  The case timeline UI renders directly from these rows — nothing is
  hardcoded (spec section 64). Metadata is scrubbed of any key that looks
  like a credential as defense in depth.
- **Simulated clock (`app/services/simulation_clock.py`)** — a single
  `sim_clock` DB row is the application's only notion of "now" while
  `SIMULATION_MODE=true`. `POST /api/simulate/advance-time` /
  `advance-to-deadline` move it; nothing else touches real wall-clock time
  for policy math.
- **n8n** — owns *when* the follow-up recheck fires. See
  [`../n8n/README.md`](../n8n/README.md) for why the actual recheck/decide/act
  logic still lives in the backend (`FollowupService.execute_due_followup`)
  and why the demo remains fully functional even without n8n Cloud wired up.
- **Frontend (`frontend/app`)** — `/` and `/customer` render the customer
  chat experience with a live case status card; `/cases/[caseId]` renders
  the audit-driven timeline; `/operations` is the human dashboard with
  metrics, a case list, and Approve/Override actions. All three read the
  same REST API — the UI holds no business logic.

## Memory: Cognee (semantic layer)

`MemoryService` (`app/services/memory_service.py`) has two halves, layered
additively:

1. **Database-backed (original, unchanged)** — `get_customer_context`,
   `get_open_cases`, `get_recent_transactions`, `get_previous_messages`,
   `save_interaction`. This is authoritative structured state and is all
   the app needs to function; nothing below can break it.
2. **Cognee-backed (semantic memory)** — `remember_customer_interaction`,
   `remember_case_event`, `remember_resolution`, `retrieve_customer_memory`,
   `retrieve_case_memory`, `retrieve_related_incidents`. These call
   `CogneeMemoryService` (`app/integrations/cognee/cognee_memory_service.py`),
   a small `httpx` REST client against **Cognee Cloud**
   (`POST {COGNEE_BASE_URL}/api/v1/remember` /
   `POST {COGNEE_BASE_URL}/api/v1/search`, authenticated with an
   `X-Api-Key` header) — modeled deliberately on the existing `N8nClient`:
   plain sync HTTP, never raises, logs and degrades on failure.

**Why REST against Cognee Cloud and not the local `cognee` pip SDK's
in-process pipeline:** the local SDK's `remember()`/`cognify()` needs its
own LLM key and local vector/graph database to build the knowledge graph —
exactly the kind of local infrastructure setup this prototype avoids
elsewhere too (spec section 24). Cognee Cloud is a hosted, per-tenant REST
API (what the hackathon's Cognee credits are for) that manages the
LLM/graph pipeline server-side; the app only needs `COGNEE_API_KEY` and
`COGNEE_BASE_URL`. This was verified against the installed `cognee==1.5.4`
package and `docs.cognee.ai` on 2026-09-18 — see the "Cognee Memory"
section in the root README for what's confirmed vs. what still needs
verification against real credentials.

**What goes into Cognee, and how:** never a raw customer message, an ORM
row, or a credential. `app/integrations/cognee/memory_formatters.py`
builds deterministic, paraphrased text from already-verified structured
fields only (customer name, amount, merchant, policy result, outcome) —
the same discipline as `generate_response`'s verified-facts contract. This
is a structural guarantee, not a redaction step: there is no code path
where `MemoryService.remember_*` is ever handed the raw message string.
Writes happen at five points chosen for narrative significance, not every
DB row: case created, dispute raised, human override, case resolved, and
the follow-up recheck outcome (spec section 8) — plus a customer-interaction
note after each `/chat` turn, which is backgrounded via FastAPI
`BackgroundTasks` so a Cognee Cloud round trip never adds latency to the
customer-facing response.

**`ContextAssembler`** (`app/services/context_assembler.py`) is the single
place DB context and Cognee's `retrieve_customer_memory` are combined into
one dict, returned to the `retrieve_context` node via the `assemble_context`
tool. Its output includes a `semantic_memory` list that flows into
`generate_response`'s prompt as explicitly-labeled "context only, NOT
authoritative" background — and into the `/chat` response's `context_used`
summary and the case-detail `memory` section, both of which report *whether*
context was found, never raw memory content, to the customer/operator.

**What Cognee is never allowed to do:** decide policy, change a
transaction/case/dispute status, or gate an escalation. `decide_next_action`
never reads `semantic_memory` — the high-value threshold, breach detection,
and every state transition come only from `PolicyEngine` and the database,
exactly as before this integration. A Cognee outage (timeout, bad
credentials, wrong endpoint) makes `CogneeMemoryService` return `{"stored":
false, ...}` / `[]`, logged as `COGNEE_MEMORY_WRITE`/`COGNEE_UNAVAILABLE`;
the rest of the request proceeds exactly as it would with Cognee disabled.

## Idempotency

`case_id + action_type` (or an equivalent unique constraint) guards every
irreversible action:

- `CaseService.get_or_create_case` reuses an open case for the same
  transaction instead of creating a duplicate — this is also what makes
  contextual follow-ups ("Abhi tak paise nahi aaye") land on the same case.
- `FollowupService.schedule` reuses an active (`SCHEDULED`/`RUNNING`)
  follow-up per case.
- `DisputeService.raise_dispute` reuses an existing dispute per case.
- `FollowupService.execute_due_followup` is a no-op if the follow-up is
  already `COMPLETED`, so n8n calling it twice (or the simulated-clock
  fallback firing alongside a configured n8n webhook) never double-raises a
  dispute.

## What's deliberately out of scope

Real Paytm/NPCI APIs, real money movement, production auth, a full fraud
engine, and the non-payment product lines (travel/loans/insurance/shopping)
are all out of scope for this slice — see spec section 5.3. The service
boundaries above exist specifically so those can be swapped in later without
touching the agent or rules engine.
