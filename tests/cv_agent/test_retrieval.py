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
