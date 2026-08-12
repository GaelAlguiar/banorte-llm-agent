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
