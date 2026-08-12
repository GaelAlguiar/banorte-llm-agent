from dataclasses import dataclass
from typing import Protocol

from cv_agent.agent.prompts import build_instructions
from cv_agent.agent.tools import ProfileTools
from cv_agent.api.models import UserAttachment
from cv_agent.retrieval.base import RetrievalService
from cv_agent.security.privacy_intent import (
    classify_dual_use_intent,
    is_sensitive_request,
)
from cv_agent.skills.models import AgentSkill
from cv_agent.retrieval.text import tokenize


class ModelClient(Protocol):
    def generate(
        self,
        *,
        question: str,
        evidence: list[dict],
        skill: AgentSkill,
        instructions: str,
        attachments: tuple[UserAttachment, ...] = (),
        reasoning_effort: str | None = None,
    ) -> str:
        ...


@dataclass(frozen=True)
class AgentAnswer:
    text: str
    skill_name: str
    evidence_ids: tuple[str, ...]


class CvAgentService:
    def __init__(
        self,
        retrieval: RetrievalService,
        skills: list[AgentSkill],
        model: ModelClient,
    ):
        self.retrieval = retrieval
        self.skills = skills
        self.model = model
        self.tools = ProfileTools(retrieval)

    def _select_skill(self, question: str) -> AgentSkill:
        question_tokens = set(tokenize(question))
        dual_use_intent = classify_dual_use_intent(question)
        if is_sensitive_request(question):
            return next(
                skill
                for skill in self.skills
                if skill.name == "privacy_guard"
            )
        scores = {name: 0 for name in ("role_fit", "architecture_explainer", "learning_evidence", "project_story")}
        scores["architecture_explainer"] += 5 * len(question_tokens & {"arquitectura", "rag", "terraform", "apim", "infraestructura"})
        scores["architecture_explainer"] += 2 * len(question_tokens & {"a2a", "aks", "container", "dns", "embeddings", "mcp", "redes", "llms", "backend", "frontend", "apis", "produccion"})
        if dual_use_intent == "educational":
            scores["architecture_explainer"] += 4
        scores["learning_evidence"] += 5 * len(question_tokens & {"aprende", "aprenderia", "aprendizaje", "autodidacta", "domina", "mejora", "persistente", "trasladaria", "fine", "tuning"})
        if dual_use_intent == "professional":
            scores["learning_evidence"] += 4
        scores["project_story"] += 5 * len(question_tokens & {"proyecto", "proyectos"})
        scores["project_story"] += 3 * len(question_tokens & {"automatizacion", "automatizaciones", "cotizacion", "cotizaciones", "construyo", "impacto", "resolvio", "whatsapp", "jira", "chatbot", "github"})
        enerey_context = "enerey" in question_tokens
        ios_application_context = bool(
            question_tokens & {"ios", "app", "aplicacion"}
        )
        operational_lookup_context = bool(
            question_tokens
            & {
                "trabajador", "trabajadores", "datos", "excel",
                "consultaban", "informacion", "base", "bases",
            }
        )
        if enerey_context and ios_application_context and operational_lookup_context:
            scores["project_story"] += 4
        conversational_application_context = bool(
            question_tokens & {"conversacional", "conversacion", "consulta"}
            and ios_application_context
        )
        operational_problem_context = bool(
            question_tokens
            & {
                "problema", "operativo", "necesidad", "resolvia", "solucionaba",
                "servia", "trabajadores", "datos", "excel",
            }
        )
        if (
            enerey_context
            and conversational_application_context
            and operational_problem_context
        ):
            scores["project_story"] += 5
        enerey_experience_context = bool(
            enerey_context
            and (
                question_tokens & {"conversacional", "conversacion"}
                or (
                    ios_application_context
                    and question_tokens & {"empleado", "empleados", "trabajador", "trabajadores"}
                )
            )
        )
        if enerey_experience_context:
            scores["project_story"] += 5
        freelance_site_context = bool(
            question_tokens & {"freelance", "independiente", "modalidad"}
            and question_tokens
            & {"sitio", "sitios", "web", "pagina", "paginas", "global", "lugra"}
        )
        named_site_context = bool(
            question_tokens & {"global", "lugra"}
            and question_tokens
            & {
                "participacion", "participo", "desarrollo", "creo", "trabajo",
                "modalidad", "sitio", "sitios", "pagina", "paginas",
            }
        )
        global_lugra_context = {"global", "lugra"} <= question_tokens
        if freelance_site_context or named_site_context or global_lugra_context:
            scores["project_story"] += 5
        if question_tokens & {"participacion", "participo"} and question_tokens & {"chatbot", "documentos", "servicios", "proyecto"}:
            scores["project_story"] += 5
        if question_tokens & {"contratar", "elegir", "vacante", "banorte", "aportaria", "diferencia"}:
            scores["role_fit"] += 5
        if question_tokens & {"candidato", "candidatos"} and question_tokens & {"por", "valioso", "aportaria", "diferencia"}:
            scores["role_fit"] += 4
        if {"primeros", "meses"} <= question_tokens:
            scores["role_fit"] += 5
        best_name, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score:
            return next(skill for skill in self.skills if skill.name == best_name)
        scored: list[tuple[int, AgentSkill]] = []
        for skill in self.skills:
            examples = set(tokenize(" ".join(skill.intent_examples)))
            scored.append((len(question_tokens & examples), skill))
        score, selected = max(scored, key=lambda item: item[0])
        if score == 0:
            return next(
                skill
                for skill in self.skills
                if skill.name == "profile_summary"
            )
        return selected

    def answer(
        self,
        question: str,
        attachments: tuple[UserAttachment, ...] = (),
        reasoning_effort: str | None = None,
    ) -> AgentAnswer:
        if not question.strip():
            raise ValueError("La pregunta no puede estar vacía")
        skill = self._select_skill(question)
        evidence = []
        if skill.name != "privacy_guard":
            allowed_document_ids = {
                document.id
                for document in self.retrieval.documents
                if document.source_path in skill.allowed_sources
            }
            evidence = self.tools.search_profile(
                question,
                categories=list(skill.allowed_categories),
                top_k=8,
                allowed_document_ids=allowed_document_ids,
            )
            if not evidence:
                evidence = self.tools.search_profile(
                    question,
                    top_k=3,
                    allowed_document_ids=allowed_document_ids,
                )
            if (
                skill.name == "profile_summary"
                and evidence
                and evidence[0]["score"] < 0.45
            ):
                evidence = []
        text = self.model.generate(
            question=question,
            evidence=evidence,
            skill=skill,
            instructions=build_instructions(),
            attachments=attachments,
            reasoning_effort=reasoning_effort,
        ).strip()
        return AgentAnswer(
            text=text,
            skill_name=skill.name,
            evidence_ids=tuple(
                item["document_id"] for item in evidence
            ),
        )
