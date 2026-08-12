from pathlib import Path
import re
import unicodedata

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
        source_path=f"knowledge/{path.name}",
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


DEFAULT_SPLIT_THRESHOLD = 1_200
DEFAULT_MAX_CHUNK_CHARS = 1_200
DEFAULT_OVERLAP_CHARS = 120
_HEADING = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    compact = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return compact or "seccion"


def _section_parts(text: str) -> list[tuple[str | None, str]]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [(None, text.strip())]
    parts: list[tuple[str | None, str]] = []
    introduction = text[:matches[0].start()].strip()
    if introduction:
        parts.append(("Introducción", introduction))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        heading = match.group(2).strip().rstrip("#").strip()
        # Include the heading in the embedded excerpt so lexical retrieval can
        # find concepts expressed primarily by section titles.
        parts.append((heading, f"{match.group(1)} {heading}\n\n{body}".strip()))
    return parts


def _chunks_for_document(
    document: KnowledgeDocument,
    *,
    split_threshold: int,
    max_chunk_chars: int,
    overlap_chars: int,
) -> list[KnowledgeDocument]:
    parts = _section_parts(document.text)
    if len(document.text) < split_threshold and len(document.text) <= max_chunk_chars:
        return [KnowledgeDocument(
            **{
                **document.__dict__,
                "document_id": document.id,
                "chunk_id": document.id,
                "section": None,
            }
        )]
    chunks: list[KnowledgeDocument] = []
    seen_slugs: dict[str, int] = {}
    for section, text in parts:
        section_name = section or "Introducción"
        base_slug = _slug(section_name)
        occurrence = seen_slugs.get(base_slug, 0) + 1
        seen_slugs[base_slug] = occurrence
        suffix = base_slug if occurrence == 1 else f"{base_slug}-{occurrence}"
        subchunks = _bounded_parts(text, max_chunk_chars, overlap_chars)
        for part_index, subchunk in enumerate(subchunks, start=1):
            part_suffix = (
                f"--part-{part_index:02d}" if len(subchunks) > 1 else ""
            )
            chunks.append(KnowledgeDocument(
                **{
                    **document.__dict__,
                    "title": f"{document.title} — {section_name}",
                    "text": subchunk,
                    "document_id": document.id,
                    "chunk_id": f"{document.id}--{suffix}{part_suffix}",
                    "section": section_name,
                }
            ))
    return chunks


def _bounded_parts(text: str, limit: int, overlap: int) -> list[str]:
    if limit < 200 or overlap < 0 or overlap >= limit:
        raise ValueError("Configuración de chunks inválida")
    if len(text) <= limit:
        return [text]
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= limit:
            units.append(paragraph)
            continue
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > limit:
                units.append(current)
                current = word
            else:
                current = candidate
        if current:
            units.append(current)
    result: list[str] = []
    current_units: list[str] = []
    for unit in units:
        candidate = "\n\n".join([*current_units, unit])
        if current_units and len(candidate) > limit:
            completed = "\n\n".join(current_units)
            result.append(completed)
            overlap_units: list[str] = []
            overlap_length = 0
            for previous in reversed(current_units):
                added = len(previous) + (2 if overlap_units else 0)
                if overlap_length + added > overlap:
                    break
                overlap_units.insert(0, previous)
                overlap_length += added
            current_units = [*overlap_units, unit]
            while len("\n\n".join(current_units)) > limit and overlap_units:
                overlap_units.pop(0)
                current_units = [*overlap_units, unit]
        else:
            current_units.append(unit)
    if current_units:
        result.append("\n\n".join(current_units))
    return result


def load_knowledge_chunks(
    directory: Path,
    *,
    split_threshold: int = DEFAULT_SPLIT_THRESHOLD,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[KnowledgeDocument]:
    """Load authorized source documents as stable, heading-aware chunks.

    Small documents intentionally remain one chunk. Longer Markdown sources are
    split at semantic heading boundaries without losing parent provenance.
    """
    return [
        chunk
        for document in load_knowledge(directory)
        for chunk in _chunks_for_document(
            document,
            split_threshold=split_threshold,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
    ]
