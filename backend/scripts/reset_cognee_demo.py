"""Reset ONLY the Nishchint demo dataset in Cognee Cloud (spec section 31).

This is a manual, explicitly-confirmed script — never exposed through the
app's API or UI, and never touches the application database (that's what
POST /api/simulate/reset is for). It only deletes the single dataset named
by COGNEE_DATASET (default "nishchint_memory"), not anything else in your
Cognee Cloud account.

Verified against a real Cognee Cloud account on 2026-09-18:
`DELETE /api/v1/datasets/{dataset_id}` needs the dataset's UUID, not its
name (a name gives a 422 "uuid_parsing" error) — so this first resolves the
name via `GET /api/v1/datasets`. Also note: `GET /api/v1/datasets` 307-
redirects without a trailing slash, hence `follow_redirects=True` below.

Usage:
    cd backend
    source .venv/bin/activate
    python -m scripts.reset_cognee_demo --yes
"""

import sys

import httpx

from app.config import cognee_configured, get_settings


def main() -> int:
    settings = get_settings()
    if not cognee_configured(settings):
        print("Cognee is not configured — nothing to reset.")
        return 1

    if "--yes" not in sys.argv:
        confirm = input(
            f"This will delete Cognee dataset '{settings.cognee_dataset}' on "
            f"{settings.cognee_base_url}. Type the dataset name to confirm: "
        )
        if confirm.strip() != settings.cognee_dataset:
            print("Confirmation did not match — aborted.")
            return 1

    base_url = settings.cognee_base_url.rstrip("/")
    headers = {"X-Api-Key": settings.cognee_api_key}

    try:
        list_resp = httpx.get(f"{base_url}/api/v1/datasets", headers=headers, timeout=15.0, follow_redirects=True)
        list_resp.raise_for_status()
        datasets = list_resp.json()
        match = next((d for d in datasets if d.get("name") == settings.cognee_dataset), None)
        if match is None:
            print(f"No dataset named '{settings.cognee_dataset}' found on this account — nothing to delete.")
            return 0

        delete_resp = httpx.delete(
            f"{base_url}/api/v1/datasets/{match['id']}", headers=headers, timeout=30.0, follow_redirects=True
        )
        delete_resp.raise_for_status()
        print(f"Deleted dataset '{settings.cognee_dataset}' (id={match['id']}).")
        return 0
    except Exception as exc:
        print(
            f"FAILED to delete via REST ({exc}). Delete the '{settings.cognee_dataset}' dataset "
            f"manually from the Cognee Cloud dashboard instead."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
