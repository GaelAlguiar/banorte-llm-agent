import math
from collections import Counter
from pathlib import Path

import numpy as np

from cv_agent.knowledge.loader import load_knowledge
from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.models import RetrievalHit
from cv_agent.retrieval.embeddings import LocalEmbeddingProvider
from cv_agent.retrieval.text import tokenize


class HybridCvRetrieval:
    def __init__(
        self,
        documents: list[KnowledgeDocument],
        relevance_threshold: float = 0.45,
    ):
        self.documents = documents
        self.relevance_threshold = relevance_threshold
        self.embeddings = LocalEmbeddingProvider(dimensions=1024)
        self._vectors = {
            document.id: self.embeddings.embed(
                f"{document.title}\n{document.text}"
            )
            for document in documents
        }

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        relevance_threshold: float = 0.45,
    ) -> "HybridCvRetrieval":
        return cls(
            load_knowledge(directory),
            relevance_threshold=relevance_threshold,
        )

    def _bm25(
        self,
        query: str,
        documents: list[KnowledgeDocument],
    ) -> dict[str, float]:
        tokenized = [
            tokenize(f"{document.title} {document.text}")
            for document in documents
        ]
        query_terms = set(tokenize(query))
        average_length = sum(map(len, tokenized)) / max(
            len(tokenized),
            1,
        )
        document_frequency = Counter(
            term
            for term in query_terms
            for terms in tokenized
            if term in terms
        )
        scores: dict[str, float] = {}
        for document, terms in zip(documents, tokenized, strict=True):
            frequencies = Counter(terms)
            score = 0.0
            for term in query_terms:
                frequency = frequencies[term]
                if frequency == 0:
                    continue
                inverse_frequency = math.log(
                    1
                    + (
                        len(documents)
                        - document_frequency[term]
                        + 0.5
                    )
                    / (document_frequency[term] + 0.5)
                )
                denominator = frequency + 1.5 * (
                    0.25
                    + 0.75
                    * len(terms)
                    / max(average_length, 1)
                )
                score += inverse_frequency * (
                    frequency * 2.5
                ) / denominator
            scores[document.id] = score
        return scores

    @staticmethod
    def _rank(scores: dict[str, float]) -> list[str]:
        return [
            identifier
            for identifier, _ in sorted(
                scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    def search(
        self,
        query: str,
        top_k: int = 5,
        categories: set[str] | None = None,
    ) -> list[RetrievalHit]:
        documents = [
            document
            for document in self.documents
            if categories is None or document.category in categories
        ]
        if not documents:
            return []
        query_vector = self.embeddings.embed(query)
        query_terms = set(tokenize(query))
        employment_query = bool(
            query_terms & {"empleo", "experiencia", "laboral", "profesional"}
        )
        role_query = bool(
            query_terms
            & {
                "candidato", "candidatos", "contratar", "diferencia",
                "elegir", "vacante", "aportaria",
            }
        )
        vector_scores = {
            document.id: max(
                0.0,
                float(np.dot(query_vector, self._vectors[document.id])),
            )
            for document in documents
        }
        lexical_scores = self._bm25(query, documents)
        rankings = [
            self._rank(vector_scores),
            self._rank(lexical_scores),
        ]
        rrf_scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, identifier in enumerate(ranking, start=1):
                rrf_scores[identifier] = (
                    rrf_scores.get(identifier, 0.0)
                    + 1.0 / (60 + rank)
                )
        max_lexical = max(lexical_scores.values(), default=0.0)
        max_rrf = max(rrf_scores.values(), default=0.0)
        by_id = {document.id: document for document in documents}
        hits: list[RetrievalHit] = []
        for identifier in by_id:
            document = by_id[identifier]
            lexical = (
                lexical_scores[identifier] / max_lexical
                if max_lexical
                else 0.0
            )
            rrf = (
                rrf_scores[identifier] / max_rrf
                if max_rrf
                else 0.0
            )
            final = (
                0.55 * vector_scores[identifier]
                + 0.30 * lexical
                + 0.15 * rrf
            )
            title_terms = set(tokenize(document.title))
            exact_title_terms = query_terms & title_terms
            if exact_title_terms & {
                "terraform", "apim", "aks", "firebase", "entra",
                "whatsapp", "rag", "a2a", "mcp", "azure", "aws", "gcp",
            }:
                final += 0.40
            if employment_query and document.source_kind == "laboral":
                final += 0.22
            if role_query and document.category == "vacante":
                final += 0.25
            elif role_query and document.category == "perfil":
                final += 0.18
            if final < self.relevance_threshold:
                continue
            hits.append(
                RetrievalHit(
                    document_id=document.id,
                    title=document.title,
                    category=document.category,
                    evidence_level=document.evidence_level,
                    impact_type=document.impact_type,
                    source_kind=document.source_kind,
                    source=document.source,
                    excerpt=document.text[:1200],
                    vector_score=vector_scores[identifier],
                    lexical_score=lexical,
                    rrf_score=rrf,
                    score=final,
                )
            )
        return sorted(
            hits,
            key=lambda hit: hit.score,
            reverse=True,
        )[:max(1, min(top_k, 8))]

    def ready(self) -> bool:
        return True
