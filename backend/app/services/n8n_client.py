"""Thin client for triggering the n8n follow-up automation (spec section 50).

n8n is a first-class component, not decorative: when N8N_WEBHOOK_URL is
configured, real HTTP calls go out to it and it drives the recheck/dispute
workflow by calling back into POST /api/workflows/execute-followup.

External services are never assumed reliable (spec section 73) — every call
here is best-effort, logged, and audited; failures never crash the caller.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("nishchint.n8n")


class N8nClient:
    def __init__(self):
        self._settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self._settings.n8n_webhook_url)

    def trigger_followup_scheduled(self, payload: dict) -> dict:
        """Fire-and-forget notify n8n that a follow-up was scheduled."""
        if not self.configured:
            return {"triggered": False, "reason": "N8N_WEBHOOK_URL not configured"}
        try:
            resp = httpx.post(self._settings.n8n_webhook_url, json=payload, timeout=5.0)
            resp.raise_for_status()
            return {"triggered": True, "n8n_response": _safe_json(resp)}
        except Exception as exc:
            logger.warning("n8n webhook trigger failed: %s", exc)
            return {"triggered": False, "reason": str(exc)}

    def trigger_followup_due(self, payload: dict) -> dict:
        """Tell n8n a scheduled follow-up is due now (used by the demo clock
        when it crosses a followup's scheduled_for)."""
        return self.trigger_followup_scheduled(payload)


def _safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return resp.text[:500]


n8n_client = N8nClient()
