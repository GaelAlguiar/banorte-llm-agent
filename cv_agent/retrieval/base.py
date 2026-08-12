from typing import Protocol

from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.models import RetrievalHit


class RetrievalService(Protocol):
    documents: list[KnowledgeDocument]

    def search(
        self,
        query: str,
        top_k: int = 5,
        categories: set[str] | None = None,
        allowed_document_ids: set[str] | None = None,
    ) -> list[RetrievalHit]:
        ...

    def ready(self) -> bool:
        ...
