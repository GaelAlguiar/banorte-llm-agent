from dataclasses import dataclass
import ipaddress
from typing import Protocol
from urllib.parse import urlsplit

from cv_agent.agent.prompts import build_instructions
from cv_agent.agent.professional_intent import (
    FailSafeProfessionalIntentClassifier,
    ProfessionalIntentClassifier,
)
from cv_agent.agent.tools import ProfileTools
from cv_agent.api.models import UserAttachment
from cv_agent.retrieval.base import RetrievalService
from cv_agent.security.privacy_intent import (
    PrivacyIntentClassifier,
    direct_privacy_decision,
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
class AnswerEvidence:
    document_id: str
    chunk_id: str
    title: str
    section: str | None
    public_url: str | None
    source_kind: str
    evidence_level: str
    impact_type: str
    confidence: str


@dataclass(frozen=True)
class AgentAnswer:
    text: str
    skill_name: str
    evidence_ids: tuple[str, ...]
    evidence: tuple[AnswerEvidence, ...] = ()


_PUBLIC_EVIDENCE_URLS = {
    "https://enereylatam.com/",
    "https://apps.apple.com/mx/app/enerey/id6736633080",
    "https://globalfls.com/",
    "https://www.lugramx.com/",
}


def _public_source_url(source: str) -> str | None:
    for candidate in source.replace(",", " ").replace(";", " ").split():
        value = candidate.strip("()[]<>.\"")
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname:
            continue
        hostname = parsed.hostname.lower()
        try:
            if ipaddress.ip_address(hostname).is_private:
                continue
        except ValueError:
            pass
        try:
            port = parsed.port
        except ValueError:
            continue
        if parsed.username or parsed.password or port not in (None, 443):
            continue
        if parsed.query or parsed.fragment:
            continue
        path = parsed.path or "/"
        canonical = parsed._replace(
            scheme="https", netloc=hostname, path=path.rstrip("/") or "/",
            query="", fragment="",
        ).geturl()
        if canonical in _PUBLIC_EVIDENCE_URLS:
            return canonical
    return None


def _confidence_bucket(item: dict) -> str:
    score = float(item.get("score", 0.0))
    if item.get("evidence_level") == "directa" and score >= 0.65:
        return "alta"
    if score >= 0.35:
        return "media"
    return "contextual"


class CvAgentService:
    def __init__(
        self,
        retrieval: RetrievalService,
        skills: list[AgentSkill],
        model: ModelClient,
        privacy_classifier: PrivacyIntentClassifier,
        professional_classifier: ProfessionalIntentClassifier | None = None,
        trusted_benign_questions: tuple[str, ...] = (),
    ):
        self.retrieval = retrieval
        self.skills = skills
        self.model = model
        self.privacy_classifier = privacy_classifier
        self.professional_classifier = (
            professional_classifier or FailSafeProfessionalIntentClassifier()
        )
        self.trusted_benign_questions = frozenset(trusted_benign_questions)
        self.tools = ProfileTools(retrieval)

    def _select_skill(self, question: str) -> AgentSkill | None:
        question_tokens = set(tokenize(question))
        scores = {
            name: 0
            for name in (
                "role_fit", "architecture_explainer", "learning_evidence",
                "project_story", "capability_advisor", "behavioral_interview",
            )
        }
        behavioral_terms = {
            "debilidad", "debilidades", "presion", "error", "errores",
            "conflicto", "conflictos", "feedback", "retroalimentacion",
            "scrum", "fracaso", "fallo", "liderazgo", "lidera", "liderar",
            "lideraria", "colabora", "colaboracion",
        }
        scores["behavioral_interview"] += 7 * len(
            question_tokens & behavioral_terms
        )
        named_capability_terms = {
            "databricks", "react", "crewai", "framework", "frameworks",
        }
        scores["capability_advisor"] += 7 * len(
            question_tokens & named_capability_terms
        )
        adjacent_practice_terms = {
            "ci", "cd", "mlops", "monitoreo", "monitorizacion", "owasp",
            "adoptar", "adoptaria",
        }
        scores["capability_advisor"] += 4 * len(
            question_tokens & adjacent_practice_terms
        )
        scores["architecture_explainer"] += 5 * len(question_tokens & {"arquitectura", "rag", "terraform", "apim", "infraestructura"})
        scores["architecture_explainer"] += 2 * len(question_tokens & {"a2a", "aks", "azure", "container", "dns", "embeddings", "mcp", "redes", "llms", "backend", "frontend", "apis", "produccion"})
        dual_use_terms = question_tokens & {"token", "tokens", "prompt", "prompts"}
        if dual_use_terms:
            scores["architecture_explainer"] += 4
        scores["learning_evidence"] += 5 * len(question_tokens & {"aprende", "aprenderia", "aprendizaje", "autodidacta", "domina", "mejora", "persistente", "trasladaria", "fine", "tuning"})
        scores["learning_evidence"] += 7 * len(
            question_tokens & {"langchain", "agents", "sdk", "adk"}
        )
        if dual_use_terms and question_tokens & {
            "experiencia", "usa", "uso", "trabajado", "proyectos", "tokenizacion",
        }:
            scores["learning_evidence"] += 6
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
        if "enerey" in question_tokens and "hizo" in question_tokens:
            scores["project_story"] += 8
        if {"proyecto", "importante"} <= question_tokens:
            scores["project_story"] += 4
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
        if "freelance" in question_tokens:
            scores["project_story"] += 8
        if dual_use_terms and {"proyectos", "hizo"} <= question_tokens:
            scores["project_story"] += 8
        if dual_use_terms and "resume" in question_tokens:
            scores["architecture_explainer"] += 8
        if question_tokens & {"participacion", "participo"} and question_tokens & {"chatbot", "documentos", "servicios", "proyecto"}:
            scores["project_story"] += 5
        if question_tokens & {"contratar", "elegir", "vacante", "banorte", "aportaria", "diferencia"}:
            scores["role_fit"] += 5
        if "valioso" in question_tokens and (
            "candidato" in question_tokens
            or {"equipo", "ia"} <= question_tokens
        ):
            scores["role_fit"] += 5
        if question_tokens & {"candidato", "candidatos"} and question_tokens & {"por", "valioso", "aportaria", "diferencia"}:
            scores["role_fit"] += 4
        if {"primeros", "meses"} <= question_tokens:
            scores["role_fit"] += 5
        best_name, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score:
            return next(skill for skill in self.skills if skill.name == best_name)
        if "experiencia" in question_tokens and question_tokens & {
            "enerey", "heytech", "banregio",
        }:
            return next(
                skill for skill in self.skills
                if skill.name == "profile_summary"
            )
        if (
            {"experiencia", "laboral"} <= question_tokens
            and question_tokens & {"ia", "inteligencia", "artificial"}
        ):
            return next(
                skill for skill in self.skills
                if skill.name == "profile_summary"
            )
        return None

    @staticmethod
    def _needs_safe_fallback(skill: AgentSkill, evidence: list[dict]) -> bool:
        if not evidence:
            return True
        if skill.name in {"capability_advisor", "behavioral_interview"}:
            return evidence[0]["score"] < 0.30
        return False

    @staticmethod
    def _retrieval_categories(skill: AgentSkill, question: str) -> list[str]:
        question_tokens = set(tokenize(question))
        if skill.name == "profile_summary" and "trayectoria" in question_tokens:
            return ["experiencia"]
        return list(skill.allowed_categories)

    def answer(
        self,
        question: str,
        attachments: tuple[UserAttachment, ...] = (),
        reasoning_effort: str | None = None,
    ) -> AgentAnswer:
        if not question.strip():
            raise ValueError("La pregunta no puede estar vacía")
        professional_intent = None
        if question in self.trusted_benign_questions:
            privacy_decision = "benign"
        else:
            privacy_decision = direct_privacy_decision(question)
            if privacy_decision is None:
                privacy_decision = self.privacy_classifier.classify(question)
        if privacy_decision == "sensitive":
            skill = next(
                skill for skill in self.skills
                if skill.name == "privacy_guard"
            )
        else:
            skill = self._select_skill(question)
            if skill is None:
                professional_intent = self.professional_classifier.classify(question)
                skill_name = {
                    "profile": "profile_summary",
                    "capability": "capability_advisor",
                    "behavioral": "behavioral_interview",
                    "out_of_scope": "profile_summary",
                }[professional_intent]
                skill = next(item for item in self.skills if item.name == skill_name)
        evidence = []
        out_of_scope = professional_intent == "out_of_scope"
        if skill.name != "privacy_guard" and not out_of_scope:
            allowed_document_ids = {
                document.id
                for document in self.retrieval.documents
                if document.source_path in skill.allowed_sources
            }
            evidence = self.tools.search_profile(
                question,
                categories=self._retrieval_categories(skill, question),
                top_k=8,
                allowed_document_ids=allowed_document_ids,
            )
            if self._needs_safe_fallback(skill, evidence):
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
        evidence_ids = tuple(dict.fromkeys(
            item["document_id"] for item in evidence
        ))
        source_documents = {
            document.id: document for document in self.retrieval.documents
        }
        safe_evidence_items: list[AnswerEvidence] = []
        for item in evidence:
            parent = source_documents.get(item["document_id"])
            safe_evidence_items.append(AnswerEvidence(
                document_id=item["document_id"],
                chunk_id=item.get("chunk_id", item["document_id"]),
                title=item.get("title") or (
                    parent.title if parent else item["document_id"]
                ),
                section=item.get("section"),
                public_url=_public_source_url(
                    item.get("source") or (parent.source if parent else "")
                ),
                source_kind=item.get("source_kind") or (
                    parent.source_kind if parent else "perfil"
                ),
                evidence_level=item.get("evidence_level") or (
                    parent.evidence_level if parent else "transferible"
                ),
                impact_type=item.get("impact_type") or (
                    parent.impact_type if parent else "inferido"
                ),
                confidence=_confidence_bucket(item),
            ))
        safe_evidence = tuple(safe_evidence_items)
        return AgentAnswer(
            text=text,
            skill_name=skill.name,
            evidence_ids=evidence_ids,
            evidence=safe_evidence,
        )
