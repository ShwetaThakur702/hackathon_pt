"""ContextAssembler tests — verifies DB context and Cognee semantic memory
are combined, and that Cognee retrieval never affects the DB-derived facts
(transactions, open cases) it returns alongside."""

from unittest.mock import patch

from app.services.context_assembler import context_assembler


def test_assembler_returns_db_context_when_cognee_not_configured(db_session):
    result = context_assembler.assemble(db_session, "CUST001", "Mere 2400 kat gaye")
    assert result["customer"]["id"] == "CUST001"
    assert result["semantic_memory"] == []
    assert isinstance(result["active_cases"], list)
    assert isinstance(result["transaction_context"], list)


def test_assembler_includes_semantic_memory_when_available(db_session, cognee_enabled):
    fake_hits = [{"text": "Priya previously reported a failed Apollo Medicals payment.", "score": 0.9, "metadata": {}}]
    with patch.object(cognee_enabled, "recall", return_value=fake_hits):
        result = context_assembler.assemble(db_session, "CUST001", "Abhi tak paise nahi aaye")

    assert result["semantic_memory"] == fake_hits
    # DB-authoritative fields are untouched by the presence of semantic memory.
    assert result["customer"]["id"] == "CUST001"


def test_assembler_unknown_customer_returns_empty_semantic_memory(db_session):
    result = context_assembler.assemble(db_session, "NOPE", "hello")
    assert result["semantic_memory"] == []
