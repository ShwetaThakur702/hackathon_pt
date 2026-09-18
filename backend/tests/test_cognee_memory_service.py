"""CogneeMemoryService tests. All HTTP calls are mocked — no real Cognee
Cloud credentials are required (or used) here. See
backend/scripts/test_cognee.py for the manual real-credentials check."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import Settings, cognee_configured
from app.integrations.cognee.cognee_memory_service import CogneeMemoryService


def _configured_settings(**overrides) -> Settings:
    base = dict(cognee_enabled=True, cognee_api_key="test-key", cognee_base_url="https://tenant.aws.cognee.ai", cognee_dataset="nishchint_memory")
    base.update(overrides)
    return Settings(**base)


def test_cognee_configured_requires_key_and_url_and_enabled():
    assert cognee_configured(_configured_settings()) is True
    assert cognee_configured(_configured_settings(cognee_api_key="")) is False
    assert cognee_configured(_configured_settings(cognee_base_url="")) is False
    assert cognee_configured(_configured_settings(cognee_enabled=False)) is False


def test_disabled_client_never_makes_http_call():
    service = CogneeMemoryService()
    service._settings = _configured_settings(cognee_enabled=False)
    with patch("app.integrations.cognee.cognee_memory_service.httpx.post") as mock_post:
        result = service.remember("some text", "conversation", {"customer_id": "CUST001"})
        assert result == {"stored": False, "reason": "not_configured"}
        assert service.recall("query") == []
        mock_post.assert_not_called()


def test_remember_posts_expected_payload_and_headers():
    service = CogneeMemoryService()
    service._settings = _configured_settings()

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": "completed"}

    with patch("app.integrations.cognee.cognee_memory_service.httpx.post", return_value=mock_response) as mock_post:
        result = service.remember("Priya reported a failed payment.", "support_case", {"customer_id": "CUST001", "case_id": "CASE-1"})

    assert result["stored"] is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://tenant.aws.cognee.ai/api/v1/remember"
    assert kwargs["headers"]["X-Api-Key"] == "test-key"
    # Verified against a real Cognee Cloud account: /api/v1/remember takes
    # form-encoded data, not JSON — see CogneeMemoryService module docstring.
    assert kwargs["data"]["raw_data"] == "Priya reported a failed payment."
    assert kwargs["data"]["datasetName"] == "nishchint_memory"
    assert "support_case" in kwargs["data"]["node_set"]


def test_recall_parses_results():
    service = CogneeMemoryService()
    service._settings = _configured_settings()

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    # Verified real shape: a bare JSON array of per-dataset results, each
    # with a search_result list of strings (not {"results": [{"text":...}]}).
    mock_response.json.return_value = [
        {
            "dataset_id": "abc",
            "dataset_name": "nishchint_memory",
            "dataset_tenant_id": "tenant-1",
            "search_result": ["Priya previously reported a failed Apollo Medicals payment."],
        }
    ]

    with patch("app.integrations.cognee.cognee_memory_service.httpx.post", return_value=mock_response):
        results = service.recall("Abhi tak paise nahi aaye", node_name=["customer:CUST001"])

    assert len(results) == 1
    assert "Apollo Medicals" in results[0]["text"]


def test_remember_never_raises_on_http_failure():
    service = CogneeMemoryService()
    service._settings = _configured_settings()
    with patch("app.integrations.cognee.cognee_memory_service.httpx.post", side_effect=httpx.ConnectTimeout("timeout")):
        result = service.remember("text", "conversation", {})
    assert result["stored"] is False
    assert "timeout" in result["reason"].lower() or "timeout" in str(result["reason"]).lower()


def test_recall_never_raises_and_returns_empty_on_failure():
    service = CogneeMemoryService()
    service._settings = _configured_settings()
    with patch("app.integrations.cognee.cognee_memory_service.httpx.post", side_effect=httpx.ConnectError("down")):
        results = service.recall("query")
    assert results == []


def test_remember_rejects_nothing_but_never_logs_raw_secret(caplog):
    """The service itself doesn't scrub content — callers (MemoryService +
    memory_formatters) are responsible for only ever passing paraphrased,
    pre-verified text. This test documents/guards that expectation at the
    boundary: nothing about CogneeMemoryService special-cases secrets,
    which is exactly why callers must never hand it a raw message."""
    service = CogneeMemoryService()
    service._settings = _configured_settings(cognee_enabled=False)
    result = service.remember("My OTP is 998877", "conversation", {})
    assert result == {"stored": False, "reason": "not_configured"}
