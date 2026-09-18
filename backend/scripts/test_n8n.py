"""Manual real-credentials verification for n8n Cloud (mirrors
scripts/test_cognee.py). Checks:

1. N8N_BASE_URL / N8N_API_KEY can authenticate against n8n's Management
   REST API (GET /api/v1/workflows).
2. Whether the Nishchint follow-up workflow is already imported, and
   whether it's active.
3. If N8N_WEBHOOK_URL is configured, fires N8nClient.trigger_followup_scheduled
   with a harmless dummy payload to confirm the webhook itself responds.

Usage:
    cd backend
    source .venv/bin/activate
    python -m scripts.test_n8n
"""

import sys

import httpx

from app.config import get_settings
from app.services.n8n_client import n8n_client

WORKFLOW_NAME = "Nishchint - Failed Payment Follow-up"


def main() -> int:
    settings = get_settings()
    print("== Nishchint / n8n Cloud connectivity check ==")
    print(f"N8N_BASE_URL      = {settings.n8n_base_url or '(not set)'}")
    print(f"N8N_API_KEY set   = {bool(settings.n8n_api_key)}")
    print(f"N8N_WEBHOOK_URL   = {settings.n8n_webhook_url or '(not set)'}")

    if not settings.n8n_base_url or not settings.n8n_api_key:
        print("\nFAIL: N8N_BASE_URL and/or N8N_API_KEY not set in backend/.env")
        return 1

    base_url = settings.n8n_base_url.rstrip("/")

    print("\n[1/2] Authenticating against n8n Management API (GET /api/v1/workflows) ...")
    try:
        resp = httpx.get(
            f"{base_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": settings.n8n_api_key},
            timeout=15.0,
        )
        print(f"HTTP {resp.status_code}")
        if resp.status_code == 401:
            print("FAIL: authentication rejected. Double-check N8N_API_KEY (Settings > API in n8n Cloud) and that it hasn't expired.")
            return 1
        resp.raise_for_status()
        data = resp.json()
        workflows = data.get("data", data if isinstance(data, list) else [])
        print(f"OK: authenticated. {len(workflows)} workflow(s) visible to this API key.")
    except httpx.HTTPStatusError as exc:
        print(f"FAIL: {exc}. Response body: {exc.response.text[:500]}")
        return 1
    except Exception as exc:
        print(f"FAIL: could not reach {base_url} ({exc}). Check N8N_BASE_URL.")
        return 1

    match = next((w for w in workflows if w.get("name") == WORKFLOW_NAME), None)
    if match:
        print(f"\nFound workflow '{WORKFLOW_NAME}' (id={match.get('id')}, active={match.get('active')}).")
        if not match.get("active"):
            print("It exists but is NOT active — activate it in the n8n editor before demoing.")
    else:
        print(
            f"\nWorkflow '{WORKFLOW_NAME}' was not found among this API key's workflows.\n"
            "Import n8n/workflows/nishchint-followup-workflow.json into n8n Cloud, then re-run this check."
        )

    if settings.n8n_webhook_url:
        print("\n[2/2] N8N_WEBHOOK_URL is set — firing a dummy 'follow-up scheduled' event ...")
        result = n8n_client.trigger_followup_scheduled(
            {
                "case_id": "CASE-TEST-PROBE",
                "customer_id": "TEST_PROBE",
                "transaction_id": "TXN-TEST-PROBE",
                "followup_id": "FUP-TEST-PROBE",
                "scheduled_for": "2026-01-01T00:00:00",
                "action": "RECHECK_FAILED_PAYMENT",
            }
        )
        print(result)
        if not result.get("triggered"):
            print("FAIL: webhook call did not succeed — see reason above.")
            return 1
        print("OK: n8n webhook responded.")
    else:
        print(
            "\n[2/2] N8N_WEBHOOK_URL is not set yet, so the webhook itself wasn't tested.\n"
            "Once the workflow above is imported and activated, copy its 'Webhook: Follow-up "
            "Scheduled' node's production URL into N8N_WEBHOOK_URL in backend/.env and re-run this script."
        )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
