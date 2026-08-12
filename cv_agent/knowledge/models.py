from dataclasses import dataclass
from typing import Literal


EvidenceLevel = Literal["directa", "relacionada", "transferible"]
ImpactType = Literal["confirmado", "estimado", "inferido"]
SourceKind = Literal["laboral", "demostrativo", "perfil"]


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    title: str
    category: str
    evidence_level: EvidenceLevel
    impact_type: ImpactType
    source_kind: SourceKind
    source: str
    text: str
    source_path: str = ""
    # `id` remains the stable source-document identifier for backward
    # compatibility. Retrieval/indexing use `chunk_id` as the unique child key.
    document_id: str = ""
    chunk_id: str = ""
    section: str | None = None

    @property
    def parent_id(self) -> str:
        return self.document_id or self.id

    @property
    def index_id(self) -> str:
        return self.chunk_id or self.id
