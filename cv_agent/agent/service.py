from dataclasses import dataclass
import ipaddress
import uuid
import re
from typing import Protocol
from urllib.parse import urlsplit

from cv_agent.agent.prompts import build_instructions
from cv_agent.agent.professional_intent import (
    FailSafeProfessionalIntentClassifier,
    ProfessionalIntentClassifier,
)
from cv_agent.agent.tools import ProfileTools
from cv_agent.api.models import DEFAULT_ATTACHMENT_QUESTION, UserAttachment
from cv_agent.retrieval.base import RetrievalService
from cv_agent.security.privacy_intent import (
    PrivacyIntentClassifier,
    direct_privacy_decision,
)
from cv_agent.skills.models import AgentSkill
from cv_agent.retrieval.text import normalize_text, tokenize
from cv_agent.usage.meter import UsageMeter, format_usage_footer
from cv_agent.usage.models import ModelGeneration, PublicUsage


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
        max_output_tokens: int | None = None,
    ) -> ModelGeneration:
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
    retrieval_hit_count: int = 0
    source_kind_mix: tuple[str, ...] = ()
    confidence_mix: tuple[str, ...] = ()
    attachment_count: int = 0
    attachment_kinds: tuple[str, ...] = ()
    safety_decision: str = "allowed"
    usage: PublicUsage | None = None


MAX_OUTPUT_TOKENS = 1_200
_OUTPUT_TOKEN_DEFAULTS = {
    "privacy_guard": 256,
    "profile_summary": 600,
    "behavioral_interview": 700,
    "capability_advisor": 700,
    "learning_evidence": 700,
    "architecture_explainer": 900,
    "attachment_analysis": 900,
    "project_story": 900,
    "role_fit": 900,
}
_OBSERVABLE_SOURCE_KINDS = frozenset({"perfil", "laboral", "demostrativo"})
_OUT_OF_SCOPE_REDIRECT = (
    "Puedo ayudarte con la experiencia profesional de Gael, sus proyectos "
    "de IA y cloud, o su ajuste a la posición Junior."
)
_USAGE_FOOTER_SUFFIX = re.compile(
    r"(?:\n\n)?[\d,]+ tokens · \d+(?:\.\d)?% disponible\s*$"
)
_PUBLIC_REPOSITORY_URL = (
    "https://github.com/GaelAlguiar/banorte-llm-agent"
)


_PUBLIC_EVIDENCE_URLS = {
    "https://enereylatam.com/",
    "https://apps.apple.com/mx/app/enerey/id6736633080",
    "https://globalfls.com/",
    "https://www.lugramx.com/",
}


def _requests_public_repository_link(question: str) -> bool:
    normalized = normalize_text(question)
    words = set(re.findall(r"[a-z0-9]+", normalized))
    if (
        words & {"enerey", "heytech", "banregio"}
        and not words & {"agente", "cv"}
    ):
        return False
    repository_terms = {
        "github", "repo", "repositorio", "repository",
    }
    source_code_terms = (
        "codigo fuente" in normalized or "source code" in normalized
    )
    current_agent_code = (
        "codigo" in words
        and bool(words & {"agente", "cv"})
    )
    if not (words & repository_terms or source_code_terms or current_agent_code):
        return False
    locator_terms = {
        "cual", "donde", "enlace", "link", "url", "pasame",
        "comparteme", "consultar", "ver", "publicado", "acceder",
        "muestrame",
    }
    if source_code_terms or "repo" in words or "repository" in words:
        return True
    if "repositorio" in words and not words & {"repositorios", "equipo", "heytech"}:
        return True
    return bool(words & locator_terms) or current_agent_code


def _should_include_public_repository_url(question: str) -> bool:
    normalized = normalize_text(question)
    words = set(re.findall(r"[a-z0-9]+", normalized))
    if (
        words & {"enerey", "heytech", "banregio"}
        and not words & {"agente", "cv"}
    ):
        return False
    return "github" in words or _requests_public_repository_link(question)


def _needs_repository_retrieval_focus(question: str) -> bool:
    words = set(re.findall(r"[a-z0-9]+", normalize_text(question)))
    return (
        _requests_public_repository_link(question)
        and not words & {"arquitectura", "rag"}
    )


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
        usage_meter: UsageMeter | None = None,
    ):
        self.retrieval = retrieval
        self.skills = skills
        self.model = model
        self.privacy_classifier = privacy_classifier
        self.professional_classifier = (
            professional_classifier or FailSafeProfessionalIntentClassifier()
        )
        self.trusted_benign_questions = frozenset(trusted_benign_questions)
        self.usage_meter = usage_meter
        self.tools = ProfileTools(retrieval)

    def _select_skill(self, question: str) -> AgentSkill | None:
        question_tokens = set(tokenize(question))
        if _requests_public_repository_link(question):
            return next(
                skill for skill in self.skills
                if skill.name == "architecture_explainer"
            )
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

    @staticmethod
    def _scoped_document_ids(
        skill: AgentSkill,
        question: str,
        allowed_document_ids: set[str],
    ) -> set[str]:
        question_tokens = set(tokenize(question))
        if (
            _requests_public_repository_link(question)
            and "genai-banorte-agent" in allowed_document_ids
        ):
            return {"genai-banorte-agent"}
        current_cv_agent = (
            skill.name == "architecture_explainer"
            and "agente" in question_tokens
            and bool(question_tokens & {"cv", "actual"})
            and bool(
                question_tokens
                & {"rag", "arquitectura", "codigo", "construyo", "repositorio"}
            )
        )
        if current_cv_agent and "genai-banorte-agent" in allowed_document_ids:
            return {"genai-banorte-agent"}
        return allowed_document_ids

    @staticmethod
    def _uses_attachment_analysis(
        question: str,
        attachments: tuple[UserAttachment, ...],
        selected_skill: AgentSkill | None,
    ) -> bool:
        if not attachments:
            return False
        if question == DEFAULT_ATTACHMENT_QUESTION:
            return True
        attachment_terms = {
            "adjunto", "analiza", "archivo", "captura", "compara",
            "documento", "imagen", "requisito", "requisitos", "vacante",
        }
        specialized_skills = {
            "architecture_explainer", "behavioral_interview",
            "capability_advisor", "learning_evidence", "project_story",
        }
        return bool(set(tokenize(question)) & attachment_terms) and (
            selected_skill is None or selected_skill.name not in specialized_skills
        )

    def _attachment_profile_evidence(self, skill: AgentSkill) -> list[dict]:
        allowed_document_ids = {
            document.id
            for document in self.retrieval.documents
            if document.source_path in skill.allowed_sources
        }
        return self.tools.search_profile(
            "Gael perfil experiencia laboral proyectos IA GenAI cloud "
            "habilidades candidato Junior ajuste vacante",
            categories=list(skill.allowed_categories),
            top_k=8,
            allowed_document_ids=allowed_document_ids,
        )

    def privacy_decision(self, question: str) -> str:
        """Autoriza adjuntos antes de cualquier recuperación remota."""
        if question in self.trusted_benign_questions:
            return "benign"
        decision = direct_privacy_decision(question)
        if decision is not None:
            return decision
        return self.privacy_classifier.classify(question)

    def answer(
        self,
        question: str,
        attachments: tuple[UserAttachment, ...] = (),
        reasoning_effort: str | None = None,
        max_output_tokens: int | None = None,
        privacy_decision: str | None = None,
    ) -> AgentAnswer:
        if not question.strip():
            raise ValueError("La pregunta no puede estar vacía")
        professional_intent = None
        privacy_decision = privacy_decision or self.privacy_decision(question)
        if privacy_decision == "sensitive":
            skill = next(
                skill for skill in self.skills
                if skill.name == "privacy_guard"
            )
        else:
            skill = self._select_skill(question)
            if self._uses_attachment_analysis(question, attachments, skill):
                skill = next(
                    item for item in self.skills
                    if item.name == "attachment_analysis"
                )
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
        if out_of_scope:
            return AgentAnswer(
                text=_OUT_OF_SCOPE_REDIRECT,
                skill_name=skill.name,
                evidence_ids=(),
                safety_decision="allowed",
            )
        if skill.name != "privacy_guard" and not out_of_scope:
            allowed_document_ids = {
                document.id
                for document in self.retrieval.documents
                if document.source_path in skill.allowed_sources
            }
            allowed_document_ids = self._scoped_document_ids(
                skill,
                question,
                allowed_document_ids,
            )
            if skill.name == "attachment_analysis":
                evidence = self._attachment_profile_evidence(skill)
            else:
                retrieval_question = (
                    "repositorio público GitHub código arquitectura "
                    "instrucciones ejecución evidencia evaluación"
                    if _needs_repository_retrieval_focus(question)
                    else question
                )
                evidence = self.tools.search_profile(
                    retrieval_question,
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
        effective_max_output_tokens = (
            _OUTPUT_TOKEN_DEFAULTS[skill.name]
            if max_output_tokens is None
            else min(MAX_OUTPUT_TOKENS, max_output_tokens)
        )
        generation = self.model.generate(
            question=question,
            evidence=evidence,
            skill=skill,
            instructions=build_instructions(),
            attachments=(
                () if skill.name == "privacy_guard" else attachments
            ),
            reasoning_effort=(
                "low" if skill.name == "privacy_guard" else reasoning_effort
            ),
            max_output_tokens=effective_max_output_tokens,
        )
        text = generation.text.strip()
        while _USAGE_FOOTER_SUFFIX.search(text):
            text = _USAGE_FOOTER_SUFFIX.sub("", text).rstrip()
        if (
            skill.name != "privacy_guard"
            and _should_include_public_repository_url(question)
            and _PUBLIC_REPOSITORY_URL.casefold() not in text.casefold()
        ):
            text = f"{text}\n\n{_PUBLIC_REPOSITORY_URL}"
        public_usage = None
        if generation.usage is not None and self.usage_meter is not None:
            public_usage = self.usage_meter.record(
                event_id=uuid.uuid4().hex,
                usage=generation.usage,
            )
            footer = format_usage_footer(public_usage)
            if footer:
                text = f"{text}\n\n{footer}"
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
        source_kind_mix = tuple(sorted({
            item.source_kind for item in safe_evidence
            if item.source_kind in _OBSERVABLE_SOURCE_KINDS
        }))
        confidence_mix = tuple(sorted({
            item.confidence for item in safe_evidence
            if item.confidence in {"alta", "media", "contextual"}
        }))
        return AgentAnswer(
            text=text,
            skill_name=skill.name,
            evidence_ids=evidence_ids,
            evidence=safe_evidence,
            retrieval_hit_count=min(len(evidence), 8),
            source_kind_mix=source_kind_mix,
            confidence_mix=confidence_mix,
            attachment_count=min(len(attachments), 4),
            attachment_kinds=tuple(sorted({item.kind for item in attachments})),
            safety_decision=(
                "blocked" if skill.name == "privacy_guard" else "allowed"
            ),
            usage=public_usage,
        )
