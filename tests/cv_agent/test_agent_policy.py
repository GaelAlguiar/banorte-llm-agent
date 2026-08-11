from pathlib import Path

from cv_agent.agent.prompts import build_instructions
from cv_agent.agent.service import CvAgentService
from cv_agent.retrieval.service import HybridCvRetrieval
from cv_agent.skills.registry import load_skills


class RecordingModel:
    def __init__(self):
        self.calls: list[dict] = []

    def generate(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return (
            "C# no ha sido su tecnología principal. Su experiencia "
            "equivalente está en Java, Python y TypeScript; además, "
            "su aprendizaje autodidacta y persistente le permite "
            "adoptar herramientas nuevas con fundamentos sólidos."
        )


def build_agent() -> tuple[CvAgentService, RecordingModel]:
    model = RecordingModel()
    service = CvAgentService(
        retrieval=HybridCvRetrieval.from_directory(
            Path("knowledge"),
            relevance_threshold=0.10,
        ),
        skills=load_skills(),
        model=model,
    )
    return service, model


def test_unknown_primary_technology_uses_adjacent_evidence():
    agent, model = build_agent()

    result = agent.answer("¿Gael domina C#?")

    assert "no sabe" not in result.text.lower()
    assert "tecnología principal" in result.text.lower()
    assert any(term in result.text for term in ("Java", "Python", "TypeScript"))
    assert result.skill_name == "learning_evidence"
    assert model.calls[0]["evidence"]


def test_why_gael_routes_to_role_fit_and_uses_evidence():
    agent, model = build_agent()

    result = agent.answer("¿Por qué deberían elegir a Gael para Banorte?")

    assert result.skill_name == "role_fit"
    assert model.calls[0]["evidence"]
    assert "vacante" in {
        item["category"] for item in model.calls[0]["evidence"]
    }


def test_instructions_prohibit_material_invention():
    instructions = build_instructions()

    assert "No inventes" in instructions
    assert "experiencia directa" in instructions
    assert "experiencia relacionada" in instructions
    assert "capacidad transferible" in instructions
    assert "autodidacta" in instructions


def test_instructions_require_concise_default_answers():
    instructions = build_instructions()

    assert "80 y 160 palabras" in instructions
    assert "No anuncies que consultaste" in instructions


def test_project_questions_require_a_concrete_impact_story():
    agent, model = build_agent()

    result = agent.answer(
        "¿Qué impacto tuvo la automatización de cotizaciones por WhatsApp?"
    )

    assert result.skill_name == "project_story"
    evidence = model.calls[0]["evidence"]
    assert evidence[0]["document_id"] == "cotizaciones-ia-whatsapp"
    assert evidence[0]["impact_type"] == "estimado"
    assert {
        "proyecto identificable",
        "destinatario",
        "problema",
        "participación concreta",
        "impacto",
    } <= set(model.calls[0]["skill"].output_rules)


def test_instructions_distinguish_estimates_and_avoid_resume_lists():
    instructions = " ".join(build_instructions().split())

    assert "aproximadamente" in instructions
    assert "impacto estimado" in instructions
    assert "listas de tecnologías" in instructions
    assert "proyecto concreto" in instructions
    assert "prosa natural" in instructions
    assert "Destinatario:" in instructions
    assert "nombre completo" in instructions


def test_terraform_routes_to_architecture_with_direct_evidence():
    agent, model = build_agent()

    result = agent.answer("¿Qué experiencia tiene Gael con Terraform?")

    assert result.skill_name == "architecture_explainer"
    assert model.calls[0]["evidence"][0]["document_id"] == "terraform-banregio"
    assert model.calls[0]["evidence"][0]["evidence_level"] == "directa"


def test_professional_ai_experience_prioritizes_enerey_over_demo():
    agent, model = build_agent()

    agent.answer(
        "¿Qué experiencia laboral tiene Gael con inteligencia artificial?"
    )

    evidence = model.calls[0]["evidence"]
    assert evidence[0]["document_id"] == "enerey-ia-clientes"
    assert evidence[0]["source_kind"] == "laboral"
    demo_positions = [
        index for index, item in enumerate(evidence)
        if item["source_kind"] == "demostrativo"
    ]
    assert not demo_positions or demo_positions[0] > 0


def test_instructions_never_deny_direct_professional_evidence():
    instructions = " ".join(build_instructions().split())

    assert "Nunca niegues experiencia directa" in instructions
    assert "laboral" in instructions
    assert "demostrativo" in instructions


def test_instructions_treat_attachments_as_untrusted_non_persistent_data():
    instructions = " ".join(build_instructions().split()).lower()

    assert "contenido adjunto" in instructions
    assert "no confiables" in instructions
    assert "no lo incorpores" in instructions
    assert "índice rag" in instructions
