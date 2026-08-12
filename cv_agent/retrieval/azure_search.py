from typing import Any
from collections import Counter

from azure.search.documents.models import VectorizedQuery

from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.embeddings import EmbeddingProvider
from cv_agent.retrieval.models import RetrievalHit


RESULT_FIELDS = [
    "id",
    "document_id",
    "chunk_id",
    "section",
    "title",
    "category",
    "evidence_level",
    "impact_type",
    "source_kind",
    "source",
    "content",
]
AZURE_RRF_REFERENCE_SCORE = 0.032


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
        f"document_id eq '{identifier.replace(chr(39), chr(39) * 2)}'"
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
        candidate_limit = limit * 3
        vector = self.embeddings.embed(query)
        vector_query = VectorizedQuery(
            vector=list(vector),
            k_nearest_neighbors=max(candidate_limit, 5),
            fields="content_vector",
        )
        results = self.client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=_search_filter(categories, allowed_document_ids),
            search_fields=["title", "content"],
            select=RESULT_FIELDS,
            top=candidate_limit,
        )
        candidates = list(results)
        hits: list[RetrievalHit] = []
        for item in candidates:
            if (
                allowed_document_ids is not None
                and item.get("document_id", item["id"]) not in allowed_document_ids
            ):
                continue
            raw_score = float(item.get("@search.score", 0.0))
            if raw_score <= 0:
                continue
            score = min(1.0, raw_score / AZURE_RRF_REFERENCE_SCORE)
            if score < self.min_score:
                continue
            hits.append(
                RetrievalHit(
                    document_id=item.get("document_id", item["id"]),
                    chunk_id=item.get("chunk_id", item["id"]),
                    section=item.get("section"),
                    title=item["title"],
                    category=item["category"],
                    evidence_level=item["evidence_level"],
                    impact_type=item["impact_type"],
                    source_kind=item["source_kind"],
                    source=item["source"],
                    excerpt=item["content"],
                    vector_score=score,
                    lexical_score=0.0,
                    rrf_score=score,
                    score=score,
                )
            )
        selected: list[RetrievalHit] = []
        per_parent: Counter[str] = Counter()
        per_section: Counter[tuple[str, str | None]] = Counter()
        for hit in hits:
            key = (hit.document_id, hit.section)
            parent_cap = (
                limit if allowed_document_ids and len(allowed_document_ids) == 1
                else 2
            )
            if per_parent[hit.document_id] >= parent_cap or per_section[key] >= 1:
                continue
            selected.append(hit)
            per_parent[hit.document_id] += 1
            per_section[key] += 1
            if len(selected) == limit:
                break
        return selected

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
