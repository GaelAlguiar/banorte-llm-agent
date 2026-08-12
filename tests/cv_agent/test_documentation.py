from pathlib import Path

from cv_agent.web.suggestions import SUGGESTED_QUESTIONS


def test_readme_describes_active_azure_search_architecture():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "Azure AI Search" in text
    assert "identidad administrada" in text
    assert "En producción se migraría a Azure AI Search" not in text
    assert "índice en memoria" not in text
    assert "python -m cv_agent.retrieval.ingest" in text


def test_response_quality_documents_the_exact_eight_suggested_questions():
    text = Path("docs/RESPONSE_QUALITY.md").read_text(encoding="utf-8")
    section = text.split("## Preguntas iniciales alineadas con el puesto", 1)[1]
    documented = tuple(
        line.split(". ", 1)[1]
        for line in section.splitlines()
        if line[:1].isdigit() and ". " in line
    )

    assert documented == SUGGESTED_QUESTIONS


def test_platform_contract_documents_output_limits_and_stateless_continuation():
    text = Path("docs/BANORTE_PLATFORM_CONTRACT.md").read_text(encoding="utf-8")

    assert "max_output_tokens" in text
    assert "256" in text and "1,200" in text
    assert "previous_response_id" in text
    assert "no está soportado" in text
    assert "rechaza" in text and "inferior a 256" in text
    assert "nunca aumenta" in text


def test_security_documentation_promises_only_emitted_safe_dimensions():
    text = Path("docs/SECURITY.md").read_text(encoding="utf-8")

    for dimension in (
        "skill", "retrieval_hit_count", "source_kind_mix",
        "attachment_count", "safety_decision", "latency_ms", "error_type",
    ):
        assert dimension in text
    assert "prompts ni respuestas" in text
    assert "detalles del proveedor" in text
    assert "razonamiento `low`" in text
