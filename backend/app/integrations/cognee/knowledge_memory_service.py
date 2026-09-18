"""KnowledgeMemoryService abstraction (spec section 49). Not wired into the
agent — `MemoryService` (backend/app/services/memory_service.py) is the
database-backed implementation actually used, and must keep working even if
this integration is unavailable.
"""

from abc import ABC, abstractmethod


class KnowledgeMemoryService(ABC):
    @abstractmethod
    def add_customer_event(self, customer_id: str, event: dict) -> None: ...

    @abstractmethod
    def retrieve_customer_context(self, customer_id: str) -> dict: ...

    @abstractmethod
    def retrieve_related_cases(self, customer_id: str, case_id: str) -> list[dict]: ...


class UnavailableKnowledgeMemoryService(KnowledgeMemoryService):
    """Default no-op implementation used until Cognee is wired up."""

    def add_customer_event(self, customer_id: str, event: dict) -> None:
        return None

    def retrieve_customer_context(self, customer_id: str) -> dict:
        return {}

    def retrieve_related_cases(self, customer_id: str, case_id: str) -> list[dict]:
        return []


knowledge_memory_service: KnowledgeMemoryService = UnavailableKnowledgeMemoryService()
