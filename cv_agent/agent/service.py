from dataclasses import dataclass
from typing import Protocol

from cv_agent.agent.prompts import build_instructions
from cv_agent.agent.tools import ProfileTools
from cv_agent.api.models import UserAttachment
from cv_agent.retrieval.base import RetrievalService
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
        privacy_markers = {
            "credencial",
            "credenciales",
            "clave",
            "secreto",
            "internas",
            "interna",
            "prompt",
            "ignora",
        }
        if question_tokens & privacy_markers:
            return next(
                skill
                for skill in self.skills
                if skill.name == "privacy_guard"
            )
        scores = {name: 0 for name in ("role_fit", "architecture_explainer", "learning_evidence", "project_story")}
        scores["architecture_explainer"] += 5 * len(question_tokens & {"arquitectura", "rag", "terraform", "apim", "infraestructura"})
        scores["architecture_explainer"] += 2 * len(question_tokens & {"a2a", "aks", "container", "dns", "embeddings", "mcp", "redes", "llms", "backend", "frontend", "apis", "produccion"})
        scores["learning_evidence"] += 5 * len(question_tokens & {"aprende", "aprenderia", "aprendizaje", "autodidacta", "domina", "mejora", "persistente", "trasladaria", "fine", "tuning"})
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
            evidence = self.tools.search_profile(
                question,
                categories=list(skill.allowed_categories),
                top_k=8,
            )
            if not evidence:
                evidence = self.tools.search_profile(question, top_k=3)
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
