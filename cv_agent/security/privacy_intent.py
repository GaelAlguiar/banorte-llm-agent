import re
from typing import Literal

from cv_agent.retrieval.text import normalize_text, tokenize


DualUseIntent = Literal[
    "not_applicable",
    "educational",
    "professional",
    "sensitive",
]

DUAL_USE_TERMS = {"token", "tokens", "prompt", "prompts"}
DIRECT_SECRET_MARKERS = {
    "credencial", "credenciales", "contrasena", "contrasenas",
    "password", "passwords", "secreto", "secretos", "ignora",
}


CLAUSE_BOUNDARY = re.compile(
    r"[.!?;:\n]+|\b(?:y\s+despues|y\s+luego|ahora|despues|luego|pero)\b"
)
DEFINITION_INTENT = re.compile(r"\bque\s+(?:es|son|significa)\b")
EDUCATIONAL_STEMS = (
    "explic", "defin", "signific", "funcion", "contabil", "cuent",
    "evalu", "redact", "escrib", "mejor", "consej", "recomend",
)
PROFESSIONAL_STEMS = (
    "experien", "usa", "uso", "utiliz", "trabaj", "proyect",
    "implement", "aplic", "engineering", "tokeniz",
)
def _has_stem(tokens: set[str], stems: tuple[str, ...]) -> bool:
    return any(
        token.startswith(stem)
        for token in tokens
        for stem in stems
    )


def _clauses(question: str) -> tuple[str, ...]:
    normalized = normalize_text(question)
    return tuple(
        clause.strip(" ¿¡,\t")
        for clause in CLAUSE_BOUNDARY.split(normalized)
        if clause.strip(" ¿¡,\t")
    )


def _classify_clause(
    clause: str,
    *,
    inherited_dual_use: bool,
) -> DualUseIntent:
    tokens = set(tokenize(clause))
    terms = tokens & DUAL_USE_TERMS
    if not terms and not inherited_dual_use:
        return "not_applicable"

    definition = bool(terms and DEFINITION_INTENT.search(clause))
    educational = bool(
        terms
        and (
            definition
            or _has_stem(tokens, EDUCATIONAL_STEMS)
        )
    )
    professional = bool(
        terms and _has_stem(tokens, PROFESSIONAL_STEMS)
    )

    if terms & {"prompt", "prompts"} and "sistema" in tokens:
        return "sensitive"
    if terms & {"token", "tokens"}:
        if "acceso" in tokens and not definition:
            return "sensitive"
    if re.search(
        r"\b(?:mi|mis|tu|tus)\s+(?:token|tokens|prompt|prompts)\b",
        clause,
    ):
        return "sensitive"
    if inherited_dual_use and not terms:
        return "sensitive"
    if educational:
        return "educational"
    if professional:
        return "professional"
    return "sensitive"


def classify_dual_use_intent(question: str) -> DualUseIntent:
    dual_use_seen = False
    result: DualUseIntent = "not_applicable"
    for clause in _clauses(question):
        terms = set(tokenize(clause)) & DUAL_USE_TERMS
        if not dual_use_seen and not terms:
            continue
        decision = _classify_clause(
            clause,
            inherited_dual_use=dual_use_seen and not terms,
        )
        if decision == "sensitive":
            return decision
        if decision == "professional":
            result = decision
        elif decision == "educational" and result == "not_applicable":
            result = decision
        dual_use_seen = dual_use_seen or bool(terms)
    return result


def is_sensitive_request(question: str) -> bool:
    tokens = set(tokenize(question))
    if tokens & DIRECT_SECRET_MARKERS:
        return True

    secret_key_request = bool(
        tokens & {"clave", "claves"}
        and tokens
        & {
            "dame", "dime", "muestra", "mostrar", "muestrame", "revela",
            "revelar", "secreta", "secretas", "api", "openai", "agente",
        }
    )
    private_resource_request = bool(
        tokens & {"privada", "privadas", "privado", "privados"}
        and tokens
        & {
            "url", "urls", "ruta", "rutas", "direccion", "direcciones",
            "infraestructura", "entorno", "informacion", "datos",
        }
    )
    internal_infrastructure_request = bool(
        tokens & {"interna", "internas", "interno", "internos"}
        and tokens & {"infraestructura", "entorno"}
        and tokens
        & {
            "informacion", "datos", "detalle", "detalles", "direccion",
            "direcciones",
        }
    )
    sensitive_internal_request = bool(
        tokens & {"interna", "internas", "interno", "internos"}
        and tokens
        & {
            "revela", "revelar", "muestra", "mostrar", "ruta", "rutas",
            "url", "urls", "ip", "ips", "credencial", "credenciales",
            "clave", "claves", "secreto", "secretos", "direccion",
            "direcciones",
        }
    )
    return bool(
        secret_key_request
        or private_resource_request
        or internal_infrastructure_request
        or sensitive_internal_request
        or classify_dual_use_intent(question) == "sensitive"
    )
