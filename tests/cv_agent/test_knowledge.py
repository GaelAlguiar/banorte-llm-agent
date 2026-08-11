from pathlib import Path

import pytest

from cv_agent.knowledge.loader import load_knowledge


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


def test_enterprise_portfolio_documents_are_direct_labor_evidence():
    documents = {
        item.id: item
        for item in load_knowledge(Path("knowledge"))
    }
    expected_ids = {
        "heytech-apim-chatbot",
        "heytech-terraform-multicloud",
        "heytech-ia-plataforma",
        "entrega-jira-sprints",
    }

    assert expected_ids <= documents.keys()
    for document_id in expected_ids:
        assert documents[document_id].evidence_level == "directa"
        assert documents[document_id].source_kind == "laboral"


def test_enterprise_portfolio_documents_are_safe_for_public_use():
    text = "\n".join(
        Path(f"knowledge/{number}_{name}.md").read_text(encoding="utf-8")
        for number, name in (
            (13, "heytech_apim_chatbot"),
            (14, "heytech_terraform_multicloud"),
            (15, "heytech_ia_plataforma"),
            (16, "entrega_jira"),
        )
    ).lower()
    forbidden = (
        "http://",
        "https://",
        "terraform.tfvars",
        "subscription-key",
        "personal access token",
        "10.0.",
        "/users/",
        "begin private key",
        "openai_api_key=",
        "authorization: bearer",
    )

    assert not any(marker in text for marker in forbidden)
