# Guardrails

Reference documentation for Nishchint's safety/policy boundaries — what the
agent is and isn't allowed to do, and why. This directory does not change
runtime behavior; it exists so the rules are legible in one place instead of
scattered across node/service docstrings, for review and for extending later.

Each file has a `status` per rule:

- `ACTIVE` — enforced today. The `enforced_by` field points at the exact
  module/function that does it.
- `REFERENCE_ONLY` — not wired into the running pipeline. Documented as the
  next hardening step for a real deployment, not as something the demo
  currently does. Nothing in the app reads these files at runtime.

| File | Covers |
|---|---|
| [content_safety.yaml](content_safety.yaml) | Credential/secret handling |
| [scope_boundaries.yaml](scope_boundaries.yaml) | What Nishchint will and won't engage with |
| [escalation_rules.yaml](escalation_rules.yaml) | When a human takes over |
| [financial_action_limits.yaml](financial_action_limits.yaml) | What the agent may compute/claim vs. must never invent |
| [abuse_prevention.yaml](abuse_prevention.yaml) | REFERENCE_ONLY — not implemented in this prototype |

Architectural rule these all sit under (see `app/agent/nodes.py` and
`app/rules/engine.py` docstrings): the LLM only understands language and
phrases replies — it never decides a transaction status, deadline, or
compensation amount. Every number a customer sees is computed by
`PolicyEngine` or read from the database, never generated.
