from pathlib import Path

from cv_agent.knowledge.models import KnowledgeDocument


REQUIRED_FIELDS = {
    "id",
    "title",
    "category",
    "evidence_level",
    "source",
}
EVIDENCE_LEVELS = {"directa", "relacionada", "transferible"}
IMPACT_TYPES = {"confirmado", "estimado", "inferido"}
SOURCE_KINDS = {"laboral", "demostrativo", "perfil"}


def _parse_document(path: Path) -> KnowledgeDocument:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n") or "\n---\n" not in raw[4:]:
        raise ValueError(f"Front matter inválido en {path.name}")
    header, text = raw[4:].split("\n---\n", 1)
    metadata: dict[str, str] = {}
    for line in header.splitlines():
        key, separator, value = line.partition(":")
        if not separator or not value.strip():
            raise ValueError(f"Metadato inválido en {path.name}: {line}")
        metadata[key.strip()] = value.strip()
    missing = REQUIRED_FIELDS - metadata.keys()
    if missing:
        raise ValueError(
            f"Faltan metadatos en {path.name}: {sorted(missing)}"
        )
    if metadata["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError(
            f"Nivel de evidencia inválido en {path.name}"
        )
    impact_type = metadata.get("impact_type", "confirmado")
    if impact_type not in IMPACT_TYPES:
        raise ValueError(f"Tipo de impacto inválido en {path.name}")
    source_kind = metadata.get("source_kind", "perfil")
    if source_kind not in SOURCE_KINDS:
        raise ValueError(f"Tipo de fuente inválido en {path.name}")
    return KnowledgeDocument(
        id=metadata["id"],
        title=metadata["title"],
        category=metadata["category"],
        evidence_level=metadata["evidence_level"],  # type: ignore[arg-type]
        impact_type=impact_type,  # type: ignore[arg-type]
        source_kind=source_kind,  # type: ignore[arg-type]
        source=metadata["source"],
        text=text.strip(),
    )


def load_knowledge(directory: Path) -> list[KnowledgeDocument]:
    documents: list[KnowledgeDocument] = []
    seen_ids: set[str] = set()
    for path in sorted(directory.glob("*.md")):
        document = _parse_document(path)
        if document.id in seen_ids:
            raise ValueError(f"ID duplicado: {document.id}")
        seen_ids.add(document.id)
        documents.append(document)
    if not documents:
        raise ValueError(f"No hay documentos en {directory}")
    return documents
