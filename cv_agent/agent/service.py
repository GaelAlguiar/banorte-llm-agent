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
        role_markers = {
            "banorte",
            "candidato",
            "candidatos",
            "contratar",
            "contratarlo",
            "elegir",
            "diferencia",
            "generativa",
            "vacante",
            "valioso",
        }
        if question_tokens & role_markers:
            return next(
                skill
                for skill in self.skills
                if skill.name == "role_fit"
            )
        architecture_markers = {
            "a2a", "aks", "apim", "arquitectura", "container", "dns",
            "embeddings", "infraestructura", "mcp", "rag", "redes",
            "terraform",
        }
        if question_tokens & architecture_markers:
            return next(
                skill
                for skill in self.skills
                if skill.name == "architecture_explainer"
            )
        learning_markers = {
            "aprende", "aprendizaje", "autodidacta", "c#", "domina",
            "langchain", "mejora", "persistente", "trasladaria",
        }
        if question_tokens & learning_markers:
            return next(
                skill
                for skill in self.skills
                if skill.name == "learning_evidence"
            )
        project_markers = {
            "automatizacion", "autogestor", "cotizacion", "cotizaciones",
            "construyo", "firebase", "github", "impacto", "proyecto",
            "resolvio", "reto", "whatsapp", "participacion", "jira",
            "proyectos", "empresariales",
        }
        if question_tokens & project_markers:
            return next(
                skill
                for skill in self.skills
                if skill.name == "project_story"
            )
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
