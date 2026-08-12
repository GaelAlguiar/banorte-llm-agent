from typing import Any

from azure.search.documents.models import VectorizedQuery

from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.embeddings import EmbeddingProvider
from cv_agent.retrieval.models import RetrievalHit


RESULT_FIELDS = [
    "id",
    "title",
    "category",
    "evidence_level",
    "impact_type",
    "source_kind",
    "source",
    "content",
]


def _category_filter(categories: set[str] | None) -> str | None:
    if not categories:
        return None
    expressions = [
        f"category eq '{category.replace(chr(39), chr(39) * 2)}'"
        for category in sorted(categories)
    ]
    return " or ".join(expressions)


def _document_filter(
    allowed_document_ids: set[str] | None,
) -> str | None:
    if allowed_document_ids is None:
        return None
    if not allowed_document_ids:
        return "id eq '__no_allowed_documents__'"
    expressions = [
        f"id eq '{identifier.replace(chr(39), chr(39) * 2)}'"
        for identifier in sorted(allowed_document_ids)
    ]
    return " or ".join(expressions)


def _search_filter(
    categories: set[str] | None,
    allowed_document_ids: set[str] | None,
) -> str | None:
    category_filter = _category_filter(categories)
    document_filter = _document_filter(allowed_document_ids)
    if category_filter and document_filter:
        return f"({category_filter}) and ({document_filter})"
    return category_filter or document_filter


class AzureSearchRetrieval:
    def __init__(
        self,
        *,
        documents: list[KnowledgeDocument],
        client: Any,
        embeddings: EmbeddingProvider,
        min_score: float = 0.03,
    ):
        self.documents = documents
        self.client = client
        self.embeddings = embeddings
        self.min_score = min_score

    def search(
        self,
        query: str,
        top_k: int = 5,
        categories: set[str] | None = None,
        allowed_document_ids: set[str] | None = None,
    ) -> list[RetrievalHit]:
        limit = max(1, min(top_k, 8))
        vector = self.embeddings.embed(query)
        vector_query = VectorizedQuery(
            vector=list(vector),
            k_nearest_neighbors=max(limit, 5),
            fields="content_vector",
        )
        results = self.client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=_search_filter(categories, allowed_document_ids),
            search_fields=["title", "content"],
            select=RESULT_FIELDS,
            top=limit,
        )
        hits: list[RetrievalHit] = []
        for item in results:
            if (
                allowed_document_ids is not None
                and item["id"] not in allowed_document_ids
            ):
                continue
            score = float(item.get("@search.score", 0.0))
            if score < self.min_score:
                continue
            hits.append(
                RetrievalHit(
                    document_id=item["id"],
                    title=item["title"],
                    category=item["category"],
                    evidence_level=item["evidence_level"],
                    impact_type=item["impact_type"],
                    source_kind=item["source_kind"],
                    source=item["source"],
                    excerpt=item["content"][:1200],
                    vector_score=score,
                    lexical_score=0.0,
                    rrf_score=score,
                    score=score,
                )
            )
        return hits

    def ready(self) -> bool:
        try:
            results = self.client.search(
                search_text="*",
                top=1,
                select=["id"],
            )
            next(iter(results), None)
            return True
        except Exception:
            return False
