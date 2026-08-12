from pathlib import Path

from cv_agent.retrieval.service import HybridCvRetrieval


def test_retrieval_prioritizes_genai_for_rag_question():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"),
        relevance_threshold=0.20,
    )

    hits = retrieval.search(
        "¿Cómo diseñó y evaluó Gael su sistema RAG?",
        top_k=3,
    )

    assert hits
    assert hits[0].document_id == "genai-banorte-agent"
    assert hits[0].score >= 0.20


def test_retrieval_returns_no_evidence_below_threshold():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"),
        relevance_threshold=0.72,
    )

    assert retrieval.search(
        "¿Cuál es la receta de una paella valenciana?",
        top_k=3,
    ) == []


def test_retrieval_can_filter_by_category():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"),
        relevance_threshold=0.10,
    )

    hits = retrieval.search(
        "¿Qué lo diferencia para Banorte?",
        top_k=3,
        categories={"vacante"},
    )

    assert hits
    assert {hit.category for hit in hits} == {"vacante"}


def test_retrieval_filters_the_corpus_by_allowed_document_ids_before_ranking():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "Global Lugra Enerey",
        top_k=8,
        allowed_document_ids={"freelance-global-lugra"},
    )

    assert [hit.document_id for hit in hits] == ["freelance-global-lugra"]


def test_retrieval_prioritizes_quotations_impact_story():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"),
        relevance_threshold=0.10,
    )

    hits = retrieval.search(
        "¿Qué impacto tuvo la automatización de cotizaciones por WhatsApp?",
        top_k=3,
    )

    assert hits
    assert hits[0].document_id == "cotizaciones-ia-whatsapp"
    assert hits[0].impact_type == "estimado"


def test_retrieval_prioritizes_direct_terraform_employment_story():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Qué experiencia tiene Gael con Terraform?", top_k=5
    )

    assert hits[0].document_id == "terraform-banregio"
    assert hits[0].source_kind == "laboral"
    assert hits[0].evidence_level == "directa"


def test_retrieval_prioritizes_enerey_for_professional_ai_experience():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Qué experiencia laboral tiene Gael con inteligencia artificial?",
        top_k=5,
    )

    assert hits[0].document_id == "enerey-ia-clientes"
    assert hits[0].source_kind == "laboral"
    assert "genai" not in hits[0].document_id


def test_retrieval_prioritizes_enerey_whatsapp_order_tracking_story():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Cómo funcionaba el chatbot de WhatsApp para seguimiento de pedidos?",
        top_k=5,
    )

    assert hits[0].document_id == "enerey-ia-clientes"
    assert "seguimiento personalizado" in hits[0].excerpt.lower()


def test_retrieval_prioritizes_enerey_ios_internal_assistant_story():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Qué resolvía el chatbot interno de la aplicación iOS de Enerey?",
        top_k=5,
    )

    assert hits[0].document_id == "enerey-ia-clientes"
    assert "archivos de excel" in hits[0].excerpt.lower()


def test_retrieval_prioritizes_apim_chatbot_contribution():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Cómo trabajó Gael con APIM en el chatbot empresarial?",
        top_k=5,
    )

    assert hits
    assert hits[0].document_id == "heytech-apim-chatbot"


def test_retrieval_prioritizes_jira_sprint_delivery():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Cómo organizó Gael un proyecto con Jira durante los sprints?",
        top_k=5,
    )

    assert hits
    assert hits[0].document_id == "entrega-jira-sprints"


def test_retrieval_prioritizes_confirmed_heytech_ai_participation():
    retrieval = HybridCvRetrieval.from_directory(Path("knowledge"), relevance_threshold=0.10)
    hits = retrieval.search(
        "¿Qué participación tuvo Gael en el chatbot y los servicios de análisis de documentos con IA de HeyTech?",
        top_k=5,
    )
    assert hits[0].document_id == "heytech-ia-plataforma"
    assert hits[0].evidence_level == "directa"


def test_retrieval_returns_direct_jira_workflow_evidence_for_exact_question():
    retrieval = HybridCvRetrieval.from_directory(Path("knowledge"), relevance_threshold=0.10)
    hits = retrieval.search(
        "¿Cómo organizaba Gael historias, subtareas, dependencias y entregables mediante Jira en cada sprint?",
        top_k=5,
    )
    assert hits[0].document_id == "entrega-jira-sprints"
    assert hits[0].evidence_level == "directa"


def test_multicloud_case_preserves_primary_enterprise_evidence_rank():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "Explica la conectividad que implementó entre Azure, AWS y Google Cloud.",
        top_k=8,
        categories={"proyecto", "habilidad", "historia"},
    )

    assert hits[0].document_id == "heytech-terraform-multicloud"


def test_role_fit_case_preserves_vacancy_and_profile_ranks():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Qué lo diferencia frente a otro candidato?",
        top_k=8,
        categories={"vacante", "perfil", "experiencia", "proyecto", "habilidad"},
    )
    positions = {hit.document_id: index for index, hit in enumerate(hits, 1)}

    assert positions["ajuste-vacante-banorte"] <= 4
    assert positions["perfil-gael"] <= 5


def test_enerey_stack_query_retrieves_later_serverless_integrations_section():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Qué stack usó Gael en Enerey con Firebase, Maps y Sheets?",
        top_k=5,
    )

    matching = [
        hit for hit in hits
        if hit.document_id == "proyectos-enerey"
        and hit.section == "Firebase Functions y automatización"
    ]
    assert matching
    assert all(term in matching[0].excerpt for term in ("Firebase", "Maps", "Sheets"))
    assert "Aplicación administrativa" not in matching[0].excerpt


def test_rag_query_retrieves_operational_section_beyond_old_excerpt_boundary():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Cómo operó el agente RAG con readiness, observabilidad y guardrails?",
        top_k=8,
    )

    rag_hits = [hit for hit in hits if hit.document_id == "genai-banorte-agent"]
    assert rag_hits
    assert any(
        "health/ready" in hit.excerpt and "observabilidad" in hit.excerpt.lower()
        for hit in rag_hits
    )
    assert all(len(hit.excerpt) <= 1200 for hit in rag_hits)


def test_retrieval_can_return_distinct_sections_without_duplicate_chunk_ids():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "Explica el flujo RAG, recuperación, evaluación, seguridad y operación",
        top_k=8,
        allowed_document_ids={"genai-banorte-agent"},
    )

    assert len({hit.chunk_id for hit in hits}) == len(hits)
    assert {hit.document_id for hit in hits} == {"genai-banorte-agent"}
    assert len({hit.section for hit in hits}) >= 2


def test_heytech_impact_query_retrieves_later_impact_section():
    retrieval = HybridCvRetrieval.from_directory(
        Path("knowledge"), relevance_threshold=0.10
    )

    hits = retrieval.search(
        "¿Qué impacto tuvo la fachada segura de APIM en HeyTech?",
        top_k=5,
    )

    assert hits[0].document_id == "heytech-apim-chatbot"
    assert hits[0].section == "Impacto inferido"
    assert "Cualitativamente" in hits[0].excerpt


def test_retrieval_returns_tail_subchunk_without_silent_truncation(tmp_path: Path):
    filler = "\n\n".join(
        f"Contexto operativo {index} " + ("detalle " * 35)
        for index in range(8)
    )
    content = f"""---
id: tail-project
title: Proyecto con operación extensa
category: proyecto
evidence_level: directa
source: CV
---
## Operación

{filler}

Hallazgo final: telemetriax confirma la operación posterior.
"""
    (tmp_path / "tail.md").write_text(content, encoding="utf-8")
    retrieval = HybridCvRetrieval.from_directory(
        tmp_path, relevance_threshold=0.05
    )

    hits = retrieval.search("telemetriax", top_k=3)

    assert hits[0].document_id == "tail-project"
    assert "telemetriax" in hits[0].excerpt
    assert hits[0].chunk_id.endswith("part-03") or "part-" in hits[0].chunk_id
    assert len(hits[0].excerpt) <= 1200
