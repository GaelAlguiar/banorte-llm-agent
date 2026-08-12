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


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def classify_dual_use_intent(question: str) -> DualUseIntent:
    normalized = normalize_text(question)
    tokens = set(tokenize(question))
    terms = tokens & DUAL_USE_TERMS
    if not terms:
        return "not_applicable"

    token_definition = _contains_any(
        normalized,
        (
            "que es un token", "que significa token",
            "que significa un token", "define token",
            "que son los tokens",
        ),
    )
    prompt_definition = _contains_any(
        normalized,
        (
            "que es un prompt", "que significa prompt",
            "que significa un prompt", "define prompt",
            "que son los prompts",
        ),
    )
    educational_operation = (
        bool(terms & {"token", "tokens"})
        and _contains_any(
            normalized,
            ("como funciona", "como se cuentan", "como contar"),
        )
    ) or (
        bool(terms & {"prompt", "prompts"})
        and _contains_any(
            normalized,
            (
                "como escribir", "como se evalua", "como evaluar",
                "como mejorar",
            ),
        )
    )
    educational = token_definition or prompt_definition or educational_operation

    if terms & {"prompt", "prompts"} and "sistema" in tokens:
        return "sensitive"
    if terms & {"token", "tokens"}:
        if "acceso" in tokens and not token_definition:
            return "sensitive"
    if _contains_any(
        normalized,
        (
            "cual es tu token", "cual es el token",
            "cual es tu prompt", "cual es el prompt",
            "mi token", "mi prompt",
        ),
    ):
        return "sensitive"

    professional = bool(
        "experiencia" in tokens
        or "tokenizacion" in tokens
        or (terms & {"prompt", "prompts"} and "engineering" in tokens)
    )
    if educational:
        return "educational"
    if professional:
        return "professional"
    return "sensitive"


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
