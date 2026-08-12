import json
import re
from typing import Literal, Protocol

from openai import OpenAI

from cv_agent.retrieval.text import normalize_text, tokenize


ProfessionalIntent = Literal[
    "profile", "capability", "behavioral", "out_of_scope"
]


class ProfessionalIntentClassifier(Protocol):
    def classify(self, question: str) -> ProfessionalIntent:
        ...


class FailSafeProfessionalIntentClassifier:
    def classify(self, question: str) -> ProfessionalIntent:
        return "out_of_scope"


class OpenAIProfessionalIntentClassifier:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key, timeout=8.0)
        self.model = model

    def classify(self, question: str) -> ProfessionalIntent:
        try:
            response = self.client.responses.create(
                model=self.model,
                reasoning={"effort": "none"},
                instructions=(
                    "Clasifica únicamente la intención de la pregunta, sin "
                    "responderla. Usa profile para perfil o trayectoria "
                    "profesional general; capability para tecnologías, métodos "
                    "o herramientas nuevas o adyacentes; behavioral para formas "
                    "de trabajo, liderazgo, colaboración, feedback, presión o "
                    "errores; out_of_scope para gustos, vida personal y asuntos "
                    "sin relación con la experiencia profesional o la vacante."
                ),
                input=question,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "professional_intent",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "classification": {
                                    "type": "string",
                                    "enum": [
                                        "profile", "capability", "behavioral",
                                        "out_of_scope",
                                    ],
                                }
                            },
                            "required": ["classification"],
                            "additionalProperties": False,
                        },
                    }
                },
                max_output_tokens=128,
                store=False,
            )
            value = json.loads(response.output_text)["classification"]
            if value not in {
                "profile", "capability", "behavioral", "out_of_scope",
            }:
                return "out_of_scope"
            return value
        except Exception:
            return "out_of_scope"


class DeterministicProfessionalIntentClassifier:
    """Offline semantic substitute based on intent families, not query IDs."""

    def classify(self, question: str) -> ProfessionalIntent:
        normalized = normalize_text(question)
        tokens = set(tokenize(question))
        nonprofessional_frames = (
            r"\b(?:cual|dime|indica)\b.{0,20}\bcapital\s+de\b",
            r"\b(?:clima|pronostico|temperatura)\b",
            r"\b(?:precio|cotizacion|cuanto\s+cuesta)\b.{0,30}\b(?:hoy|actual|ahora)\b",
            r"\b(?:receta|ingredientes|cocinar|cenar)\b",
            r"\b(?:marcador|partido|torneo|campeonato)\b",
        )
        professional_anchors = {
            "experiencia", "profesional", "proyecto", "proyectos",
            "habilidad", "habilidades", "vacante", "puesto", "rol",
            "trayectoria", "contratar", "candidato",
        }
        if (
            not tokens & professional_anchors
            and any(re.search(pattern, normalized) for pattern in nonprofessional_frames)
        ):
            return "out_of_scope"
        if tokens & {
            "color", "mascota", "mascotas", "libro", "comida", "platillo",
            "receta", "futbol", "deportivo", "deporte", "partido",
            "pelicula", "musica", "vacaciones",
        }:
            return "out_of_scope"
        if tokens & {
            "liderazgo", "lidera", "liderar", "lideraria", "colabora",
            "colaboracion", "feedback", "retroalimentacion", "presion",
            "error", "conflicto", "debilidad",
        } or re.search(r"\btrabaj(?:ar|ando|aria)\s+con\s+gael\b", normalized):
            return "behavioral"
        capability_frames = (
            r"\b(?:experiencia|conocimientos?|dominio)\b.{0,40}\b(?:con|de|en|usando)\b\s+\S+",
            r"\b(?:ha\s+usado|ha\s+trabajado|trabajado\s+con)\b\s+\S+",
            r"\bfundamentos\s+para\s+trabajar\s+con\b\s+\S+",
            r"\bpodria\s+(?:trabajar|desenvolverse)\b.{0,30}\b(?:con|en|usando)\b\s+\S+",
            r"\ble\s+piden\s+usar\b\s+\S+",
            r"\bque\s+tan\s+bueno\b.{0,20}\ben\b\s+\S+",
            r"\b(?:adoptar|adoptaria)\b(?:\s+una?\s+(?:plataforma|framework|herramienta))?\s+\S+",
        )
        if any(re.search(pattern, normalized) for pattern in capability_frames):
            return "capability"
        return "profile"
