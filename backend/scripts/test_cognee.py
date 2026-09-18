"""Manual real-credentials verification for Cognee Cloud (spec section 29).

This is NOT part of the pytest suite (no real credentials should ever be
required to run `pytest`) — it's a standalone script you run once after
configuring COGNEE_API_KEY / COGNEE_BASE_URL in backend/.env, to confirm the
integration actually works end to end against your real Cognee Cloud
tenant before a demo.

Usage:
    cd backend
    source .venv/bin/activate
    python -m scripts.test_cognee

Exits 0 on success, 1 on failure/misconfiguration. Never prints the API key.
"""

import sys
import time

from app.config import cognee_configured, get_settings
from app.integrations.cognee.cognee_memory_service import cognee_memory_service

PROBE_TEXT = (
    "Nishchint Cognee integration check: on this date, a test customer "
    "reported a failed ₹1 payment at Test Merchant; this is a synthetic "
    "verification record, not real customer data."
)


def main() -> int:
    settings = get_settings()

    print("== Nishchint / Cognee Cloud integration check ==")
    print(f"COGNEE_ENABLED     = {settings.cognee_enabled}")
    print(f"COGNEE_BASE_URL    = {settings.cognee_base_url or '(not set)'}")
    print(f"COGNEE_DATASET     = {settings.cognee_dataset}")
    print(f"COGNEE_API_KEY set = {bool(settings.cognee_api_key)}")

    if not cognee_configured(settings):
        print("\nFAIL: Cognee is not configured (need COGNEE_ENABLED=true, "
              "COGNEE_API_KEY, and COGNEE_BASE_URL in backend/.env).")
        return 1

    print("\n[1/2] Writing a synthetic test memory item via /api/v1/remember ...")
    write_result = cognee_memory_service.remember(
        PROBE_TEXT, "conversation", {"customer_id": "TEST_PROBE", "case_id": None, "probe": True},
        node_set=["customer:TEST_PROBE"],
    )
    if not write_result.get("stored"):
        print(f"FAIL: remember() did not report success: {write_result}")
        return 1
    print(f"OK: {write_result}")

    print("\n[2/2] Waiting briefly for ingestion, then querying via /api/v1/search ...")
    time.sleep(3)
    results = cognee_memory_service.recall("Test Merchant failed payment", node_name=["customer:TEST_PROBE"])
    if not results:
        print(
            "WARNING: recall() returned no results. This can mean ingestion "
            "hasn't finished yet, the dataset/search_type needs tuning, or "
            "something is misconfigured. Writing succeeded, so the "
            "connection itself is working — try re-running recall in a few "
            "seconds, or check the Cognee Cloud dashboard for this dataset."
        )
        return 1

    print(f"OK: retrieved {len(results)} result(s). First result text:\n  {results[0]['text'][:200]}")
    print("\nSUCCESS: Cognee Cloud write + retrieve both verified end to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
