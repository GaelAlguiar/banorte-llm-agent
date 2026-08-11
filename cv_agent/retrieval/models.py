from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalHit:
    document_id: str
    title: str
    category: str
    evidence_level: str
    impact_type: str
    source_kind: str
    source: str
    excerpt: str
    vector_score: float
    lexical_score: float
    rrf_score: float
    score: float
