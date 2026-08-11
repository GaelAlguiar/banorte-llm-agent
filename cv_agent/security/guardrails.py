import re
import unicodedata


SENSITIVE_PATTERNS = (
    r"ignora.{0,40}instrucciones",
    r"muestra.{0,30}(clave|credencial|secreto)",
    r"(prompt|instrucciones).{0,20}(sistema|internas)",
    r"(ip|direccion).{0,20}interna",
    r"ruta.{0,20}privada",
)


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    return "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )


def requests_sensitive_information(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        re.search(pattern, normalized, flags=re.DOTALL)
        for pattern in SENSITIVE_PATTERNS
    )


SAFE_PRIVACY_RESPONSE = (
    "No puedo revelar información sensible, credenciales, instrucciones "
    "internas ni detalles privados de infraestructura. Sí puedo explicar "
    "la experiencia profesional, proyectos y decisiones técnicas públicas "
    "de Gael."
)
