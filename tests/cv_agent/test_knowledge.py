import re
from pathlib import Path

import pytest

from cv_agent.knowledge.loader import load_knowledge


ENTERPRISE_KNOWLEDGE_FORBIDDEN_PATTERNS = {
    "web URL": r"https?://",
    "private 10/8 address": r"\b10(?:\.\d{1,3}){3}\b",
    "private 172.16/12 address": r"\b172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}\b",
    "private 192.168/16 address": r"\b192\.168(?:\.\d{1,3}){2}\b",
    "CIDR value": r"\b\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}\b",
    "Unix path": r"(?m)(?:^|[\s\"'=])(?:~|/)(?:[a-z0-9._-]+/)*[a-z0-9._-]+",
    "Windows path": r"\b[a-z]:\\(?:[^\s\\]+\\)*[^\s\\]+",
    "repository host": r"\b(?:github\.com|gitlab\.com|bitbucket\.org)\b",
    "repository identifier": r"(?:\bgit@|\.git\b|terraform\.tfvars)",
    "secret term": r"\b(?:password|contraseña|token|credential|credencial|api[ _-]?key|private[ _-]?key|bearer)\b",
    "UUID": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    "internal domain": r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|local|corp|lan)\b",
    "database connection URL": r"\b(?:postgres(?:ql)?|mongodb(?:\+srv)?|redis|mysql|sqlserver)://",
    "connection string field": r"\b(?:server|data source|host|accountname|accountkey|sharedaccesssignature)\s*=",
    "SAS parameter": r"(?:^|[?&])(?:sig|se|sp|sv|sr)=",
    "AWS resource identifier": r"\barn:aws[a-z-]*:[^\s]+",
    "Azure resource identifier": r"/subscriptions/[0-9a-f-]+/resourcegroups/[a-z0-9._()-]+",
}


def test_knowledge_has_core_categories():
    documents = load_knowledge(Path("knowledge"))
    categories = {document.category for document in documents}

    assert {
        "perfil",
        "experiencia",
        "proyecto",
        "habilidad",
        "vacante",
        "historia",
    } <= categories


def test_public_knowledge_contains_no_secret_markers():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("knowledge").glob("*.md")
    )
    forbidden = (
        "BEGIN PRIVATE KEY",
        "OPENAI_API_KEY=",
        "Authorization: Bearer",
        "terraform.tfstate",
        "/Users/",
    )

    assert not any(marker in text for marker in forbidden)


def test_duplicate_document_ids_are_rejected(tmp_path: Path):
    content = """---
id: repetido
title: Documento
category: perfil
evidence_level: directa
source: prueba pública
---
Contenido.
"""
    (tmp_path / "uno.md").write_text(content, encoding="utf-8")
    (tmp_path / "dos.md").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="ID duplicado"):
        load_knowledge(tmp_path)


def test_knowledge_validates_impact_type(tmp_path: Path):
    content = """---
id: impacto
title: Historia de impacto
category: proyecto
evidence_level: directa
impact_type: exagerado
source: relato profesional
---
Contenido.
"""
    (tmp_path / "impacto.md").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Tipo de impacto inválido"):
        load_knowledge(tmp_path)


def test_older_knowledge_defaults_to_confirmed_impact():
    documents = load_knowledge(Path("knowledge"))

    profile = next(item for item in documents if item.id == "perfil-gael")
    assert profile.impact_type == "confirmado"


def test_knowledge_validates_source_kind(tmp_path: Path):
    content = """---
id: fuente
title: Fuente
category: proyecto
evidence_level: directa
source_kind: publicidad
source: relato profesional
---
Contenido.
"""
    (tmp_path / "fuente.md").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Tipo de fuente inválido"):
        load_knowledge(tmp_path)


def test_older_knowledge_defaults_to_profile_source_kind():
    documents = load_knowledge(Path("knowledge"))

    profile = next(item for item in documents if item.id == "perfil-gael")
    assert profile.source_kind == "perfil"


def test_rag_story_describes_the_deployed_search_backend():
    document = next(
        item
        for item in load_knowledge(Path("knowledge"))
        if item.id == "genai-banorte-agent"
    )

    assert "Azure AI Search" in document.text
    assert "identidad administrada" in document.text
    assert "poder migrar" not in document.text


def test_enerey_ai_evidence_distinguishes_customer_and_internal_chatbots():
    document = next(
        item
        for item in load_knowledge(Path("knowledge"))
        if item.id == "enerey-ia-clientes"
    )

    text = " ".join(document.text.lower().split())
    assert "clientes" in text
    assert "seguimiento personalizado" in text
    assert {"cargado", "terminal", "ruta"} <= set(re.findall(r"\w+", text))
    assert "trabajadores" in text
    assert "aplicación ios" in text
    assert "archivos de excel" in text
    assert "acceso autorizado" in text
    assert "único desarrollador" in text
    assert "responsable técnico de extremo a extremo" in text
    assert "sin dar acceso irrestricto" in text


def test_enerey_portfolio_and_freelance_work_have_correct_authorship():
    documents = {
        item.id: " ".join(item.text.lower().split())
        for item in load_knowledge(Path("knowledge"))
    }

    enerey = documents["proyectos-enerey"]
    assert "único desarrollador" in enerey
    assert all(term in enerey for term in (
        "backend", "frontend", "integraciones", "despliegues",
        "aplicación ios", "chatbot interno", "whatsapp",
        "seguimiento de pedidos", "cotizaciones",
    ))
    assert "freelance" in enerey
    assert "global" in enerey
    assert "lugra" in enerey


def test_enterprise_portfolio_documents_have_expected_metadata(tmp_path: Path):
    filenames = (
        "13_heytech_apim_chatbot.md",
        "14_heytech_terraform_multicloud.md",
        "15_heytech_ia_plataforma.md",
        "16_entrega_jira.md",
    )
    for filename in filenames:
        source = Path("knowledge") / filename
        (tmp_path / filename).write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    documents = {item.id: item for item in load_knowledge(tmp_path)}
    expected = {
        "heytech-apim-chatbot": ("proyecto", "directa", "inferido", "laboral"),
        "heytech-terraform-multicloud": (
            "proyecto",
            "directa",
            "inferido",
            "laboral",
        ),
        "heytech-ia-plataforma": ("proyecto", "directa", "inferido", "laboral"),
        "entrega-jira-sprints": ("historia", "directa", "inferido", "laboral"),
    }

    assert documents.keys() == expected.keys()
    for document_id, metadata in expected.items():
        document = documents[document_id]
        assert (
            document.category,
            document.evidence_level,
            document.impact_type,
            document.source_kind,
        ) == metadata


def test_enterprise_portfolio_documents_match_no_known_private_markers():
    paths = tuple(Path("knowledge").glob("1[3-6]_*.md"))

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for label, pattern in ENTERPRISE_KNOWLEDGE_FORBIDDEN_PATTERNS.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            assert match is None, (
                f"{path} matched forbidden {label!r} pattern: "
                f"{match.group(0)!r}"
            )


@pytest.mark.parametrize(
    ("label", "example"),
    (
        ("web URL", "https://service.example"),
        ("private 10/8 address", "10.24.3.8"),
        ("private 172.16/12 address", "172.28.4.2"),
        ("private 192.168/16 address", "192.168.7.9"),
        ("CIDR value", "203.0.113.0/24"),
        ("Unix path", "/opt/company/config.yml"),
        ("Windows path", r"C:\work\config.yml"),
        ("repository host", "gitlab.com"),
        ("repository identifier", "git@code-host"),
        ("secret term", "api_key"),
        ("UUID", "123e4567-e89b-42d3-a456-426614174000"),
        ("internal domain", "api.platform.internal"),
        ("database connection URL", "postgresql://db-user@db-host/app"),
        ("connection string field", "AccountKey=redacted"),
        ("SAS parameter", "?sig=redacted"),
        ("AWS resource identifier", "arn:aws:iam::123456789012:role/example"),
        (
            "Azure resource identifier",
            "/subscriptions/123e4567-e89b-42d3-a456-426614174000/"
            "resourceGroups/example",
        ),
    ),
)
def test_enterprise_privacy_pattern_rejects_representative_example(
    label: str,
    example: str,
):
    pattern = ENTERPRISE_KNOWLEDGE_FORBIDDEN_PATTERNS[label]

    assert re.search(pattern, example, flags=re.IGNORECASE), label


def test_heytech_ai_document_contains_confirmed_full_evidence():
    documents = load_knowledge(Path("knowledge"))
    document = next(item for item in documents if item.id == "heytech-ia-plataforma")
    assert all(term in document.text for term in ("chatbot", "AKS", "Vertex AI", "entrenamiento"))
