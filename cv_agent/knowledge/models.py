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
