"""One-time provisioning: create + activate the Nishchint follow-up workflow
on a real n8n Cloud account via n8n's Management REST API, using
N8N_BASE_URL / N8N_API_KEY from backend/.env.

Unlike n8n/workflows/nishchint-followup-workflow.json (the portable,
importable-by-hand template that uses $env.BACKEND_BASE_URL /
$env.N8N_CALLBACK_SECRET expressions), this script inlines the actual
configured values directly into every HTTP Request node's URL, JSON body,
and Authorization header — n8n Cloud doesn't offer a simple UI for setting
custom instance environment variables, so relying on $env there is fragile.
Safe to re-run: it patches the existing workflow by name instead of
creating duplicates.

Usage:
    cd backend
    source .venv/bin/activate
    python -m scripts.setup_n8n_workflow
    python -m scripts.setup_n8n_workflow --allow-localhost   # self-hosted n8n on the same machine only
"""

import json
import secrets
import sys
from pathlib import Path

import httpx

from app.config import get_settings

WORKFLOW_NAME = "Nishchint - Failed Payment Follow-up"
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "n8n" / "workflows" / "nishchint-followup-workflow.json"
ENV_PATH = Path(__file__).parent.parent / ".env"


def _inline_env_expressions(nodes: list[dict], backend_base_url: str, callback_secret: str) -> None:
    for node in nodes:
        params = node.get("parameters", {})
        if "url" in params and isinstance(params["url"], str):
            params["url"] = params["url"].replace("{{$env.BACKEND_BASE_URL}}", backend_base_url)
        if "jsonBody" in params and isinstance(params["jsonBody"], str):
            params["jsonBody"] = params["jsonBody"].replace("$env.N8N_CALLBACK_SECRET", json.dumps(callback_secret))
        for header in params.get("headerParameters", {}).get("parameters", []):
            if isinstance(header.get("value"), str):
                header["value"] = header["value"].replace("{{$env.N8N_CALLBACK_SECRET}}", callback_secret)


def _is_localhost(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url or "0.0.0.0" in url


def _ensure_real_callback_secret(settings) -> str:
    """A default/blank N8N_CALLBACK_SECRET would mean anyone who finds the
    production webhook can call /api/workflows/followup-result or
    /notify-customer as if they were n8n (spec section 21). Auto-generate
    and persist a real one into backend/.env rather than silently deploying
    the insecure default."""
    if settings.n8n_callback_secret and settings.n8n_callback_secret != "change-me":
        return settings.n8n_callback_secret

    new_secret = secrets.token_urlsafe(32)
    print("N8N_CALLBACK_SECRET is unset or still the default 'change-me' — generating a real one.")
    if ENV_PATH.exists():
        text = ENV_PATH.read_text()
        if "N8N_CALLBACK_SECRET=" in text:
            lines = [
                f"N8N_CALLBACK_SECRET={new_secret}" if line.startswith("N8N_CALLBACK_SECRET=") else line
                for line in text.splitlines()
            ]
            ENV_PATH.write_text("\n".join(lines) + "\n")
        else:
            with ENV_PATH.open("a") as f:
                f.write(f"\nN8N_CALLBACK_SECRET={new_secret}\n")
        print(f"Wrote the new secret to {ENV_PATH} — restart the backend to pick it up.")
    else:
        print(f"WARNING: {ENV_PATH} not found — set N8N_CALLBACK_SECRET={new_secret} in backend/.env manually.")
    return new_secret


def main() -> int:
    allow_localhost = "--allow-localhost" in sys.argv

    settings = get_settings()
    if not settings.n8n_base_url or not settings.n8n_api_key:
        print("FAIL: N8N_BASE_URL / N8N_API_KEY not set in backend/.env")
        return 1

    if _is_localhost(settings.backend_base_url) and not allow_localhost:
        print(
            f"FAIL: BACKEND_BASE_URL is '{settings.backend_base_url}'. n8n Cloud cannot reach your machine — "
            "it would deploy a workflow that's broken for anyone but you, on your machine, right now.\n"
            "Fix: tunnel your backend (e.g. `ngrok http 8000`) and set BACKEND_BASE_URL to the public "
            "https://*.ngrok-free.app URL, or point it at your real deployed backend.\n"
            "Only pass --allow-localhost if n8n itself is self-hosted on this same machine/network."
        )
        return 1

    base_url = settings.n8n_base_url.rstrip("/")
    headers = {"X-N8N-API-KEY": settings.n8n_api_key, "Content-Type": "application/json"}
    callback_secret = _ensure_real_callback_secret(settings)

    template = json.loads(TEMPLATE_PATH.read_text())
    _inline_env_expressions(template["nodes"], settings.backend_base_url, callback_secret)

    payload = {
        "name": template["name"],
        "nodes": template["nodes"],
        "connections": template["connections"],
        "settings": template.get("settings", {}),
    }

    print(f"Backend base URL inlined into workflow: {settings.backend_base_url}")

    print("\nChecking for an existing workflow with this name ...")
    list_resp = httpx.get(f"{base_url}/api/v1/workflows", headers=headers, timeout=15.0)
    list_resp.raise_for_status()
    existing = next((w for w in list_resp.json().get("data", []) if w.get("name") == WORKFLOW_NAME), None)

    if existing:
        workflow_id = existing["id"]
        print(f"Found existing workflow {workflow_id} — updating it.")
        update_resp = httpx.put(f"{base_url}/api/v1/workflows/{workflow_id}", headers=headers, json=payload, timeout=15.0)
        if update_resp.status_code >= 400:
            print(f"FAIL updating workflow: {update_resp.status_code} {update_resp.text[:500]}")
            return 1
        workflow = update_resp.json()
    else:
        print("None found — creating a new workflow.")
        create_resp = httpx.post(f"{base_url}/api/v1/workflows", headers=headers, json=payload, timeout=15.0)
        if create_resp.status_code >= 400:
            print(f"FAIL creating workflow: {create_resp.status_code} {create_resp.text[:500]}")
            return 1
        workflow = create_resp.json()
        workflow_id = workflow["id"]

    print(f"Workflow id: {workflow_id}")

    if not workflow.get("active"):
        print("Activating workflow ...")
        activate_resp = httpx.post(f"{base_url}/api/v1/workflows/{workflow_id}/activate", headers=headers, timeout=15.0)
        if activate_resp.status_code >= 400:
            print(f"FAIL activating workflow: {activate_resp.status_code} {activate_resp.text[:500]}")
            print("You may need to activate it manually in the n8n editor (some accounts require this).")
        else:
            print("Activated.")
    else:
        print("Already active.")

    webhook_path = template["nodes"][0]["parameters"]["path"]
    webhook_url = f"{base_url}/webhook/{webhook_path}"
    print(f"\nProduction webhook URL: {webhook_url}")
    print("Set this as N8N_WEBHOOK_URL in backend/.env, then re-run `python -m scripts.test_n8n` to confirm the round trip.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
