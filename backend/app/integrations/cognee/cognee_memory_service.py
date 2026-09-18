"""CogneeMemoryService — thin REST client for Cognee Cloud's semantic memory
API. Modeled deliberately on app/services/n8n_client.py: plain sync httpx
calls, never raises, logs and degrades on failure.

Why REST instead of the `cognee` pip SDK: the local SDK's `remember()`/
`cognify()` pipeline needs its own LLM key and local vector/graph DB setup
to build the knowledge graph in-process — exactly the "hours of local
infrastructure" the hackathon brief says to avoid. Cognee Cloud (what the
HACKBRIVEN credits are for) is a hosted, per-tenant REST API that manages
the LLM/graph pipeline server-side; callers only need COGNEE_API_KEY and
COGNEE_BASE_URL.

Request/response shapes below are VERIFIED against a real Cognee Cloud
tenant on 2026-09-18 (see backend/scripts/test_cognee.py), not just the
published docs — which turned out to disagree on two points found by
testing:
  - POST /api/v1/remember takes multipart/form-data, NOT a JSON body (a
    JSON body gets a misleading "Either datasetId or datasetName must be
    provided" 400 even when datasetName is present). `raw_data` is a single
    string field, not a list. `external_metadata` must be a JSON-encoded
    string containing an array of objects.
  - POST /api/v1/search's response is a bare JSON array of
    {dataset_id, dataset_name, dataset_tenant_id, search_result: [str, ...]}
    — not {"results": [{"text":...}], "status": "success"} as documented.

This module is NEVER a source of truth for transaction/policy/case facts
(architectural rule — see docs/architecture.md). It stores and retrieves
paraphrased, already-verified narrative context only.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import cognee_configured, get_settings

logger = logging.getLogger("nishchint.cognee")

# Cognee Cloud search/remember calls have been observed taking many
# seconds in practice; 20s was too generous and let one slow call stall an
# entire request. Kept short deliberately — this is a "context only, never
# required" integration (see architecture docs), so timing out and
# returning [] / {"stored": False} is always safe.
REQUEST_TIMEOUT = 8.0


class CogneeMemoryService:
    def __init__(self):
        self._settings = get_settings()

    @property
    def configured(self) -> bool:
        return cognee_configured(self._settings)

    def _headers(self) -> dict:
        return {"X-Api-Key": self._settings.cognee_api_key}

    def remember(self, text: str, category: str, metadata: dict, node_set: list[str] | None = None) -> dict:
        """Store a paraphrased, already-verified memory item.

        `text` must never be a raw customer message or contain a
        credential — callers pass content built by
        app/integrations/cognee/memory_formatters.py from structured,
        already-verified fields only.
        """
        if not self.configured:
            logger.info("COGNEE_MEMORY_FALLBACK operation=remember reason=not_configured")
            return {"stored": False, "reason": "not_configured"}

        form = {
            "raw_data": text,
            "datasetName": self._settings.cognee_dataset,
            "node_set": [category, *(node_set or [])],
            "external_metadata": json.dumps([{**metadata, "category": category, "source": "nishchint", "environment": "demo"}]),
        }
        url = f"{self._settings.cognee_base_url.rstrip('/')}/api/v1/remember"
        try:
            resp = httpx.post(url, data=form, headers=self._headers(), timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            logger.info(
                "COGNEE_MEMORY_WRITE category=%s case_id=%s customer_id=%s status=ok",
                category, metadata.get("case_id"), metadata.get("customer_id"),
            )
            return {"stored": True, "response": _safe_json(resp)}
        except Exception as exc:
            logger.warning(
                "COGNEE_MEMORY_WRITE category=%s case_id=%s customer_id=%s status=failed error=%s",
                category, metadata.get("case_id"), metadata.get("customer_id"), exc,
            )
            return {"stored": False, "reason": str(exc)}

    def recall(self, query_text: str, node_name: list[str] | None = None, top_k: int | None = None) -> list[dict]:
        """Best-effort semantic search. Returns [] on any failure or when
        Cognee isn't configured — callers must treat this as optional
        enrichment, never as something the request depends on."""
        if not self.configured:
            logger.info("COGNEE_MEMORY_FALLBACK operation=recall reason=not_configured")
            return []

        payload = {
            "query": query_text,
            "datasets": [self._settings.cognee_dataset],
            "search_type": self._settings.cognee_search_type,
            "top_k": top_k or self._settings.cognee_top_k,
        }
        if node_name:
            payload["node_name"] = node_name

        url = f"{self._settings.cognee_base_url.rstrip('/')}/api/v1/search"
        try:
            resp = httpx.post(url, json=payload, headers={**self._headers(), "Content-Type": "application/json"}, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = _safe_json(resp)
            entries = data if isinstance(data, list) else []
            hits: list[dict] = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                for text in entry.get("search_result", []) or []:
                    if text:
                        hits.append({"text": text, "score": None, "metadata": {"dataset_name": entry.get("dataset_name")}})
            logger.info("COGNEE_MEMORY_RETRIEVE query_len=%s result_count=%s", len(query_text), len(hits))
            return hits
        except Exception as exc:
            logger.warning("COGNEE_UNAVAILABLE operation=recall error=%s", exc)
            return []


def _safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return None


cognee_memory_service = CogneeMemoryService()
