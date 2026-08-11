from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field


class CreateResponseRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "gael-cv-agent"
    input: str | list[dict[str, Any]]
    stream: bool = False
    previous_response_id: str | None = None
    instructions: str | None = None
    max_output_tokens: int | None = Field(default=None, ge=1)
    reasoning: "ReasoningOptions | None" = None


class ReasoningOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effort: Literal["low", "medium", "high"]


@dataclass(frozen=True)
class UserAttachment:
    kind: Literal["image", "file"]
    url: str
    filename: str | None = None


@dataclass(frozen=True)
class UserInput:
    text: str
    attachments: tuple[UserAttachment, ...] = ()


DEFAULT_ATTACHMENT_QUESTION = (
    "Analiza el archivo o imagen y relaciónalo con el perfil profesional de Gael."
)
MAX_ATTACHMENTS = 4


def _validated_https_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("El adjunto debe incluir una URL HTTPS")
    url = value.strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Los adjuntos deben usar una URL HTTPS válida")
    if parsed.username or parsed.password:
        raise ValueError("La URL HTTPS del adjunto no debe contener credenciales")
    return url


def extract_user_input(value: str | list[dict[str, Any]]) -> UserInput:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("input no puede estar vacío")
        return UserInput(text=text)
    for item in reversed(value):
        if item.get("role") != "user":
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.strip():
            return UserInput(text=content.strip())
        if isinstance(content, list):
            parts = [
                part.get("text", "").strip()
                for part in content
                if isinstance(part, dict)
                and part.get("type") in {"input_text", "text"}
                and isinstance(part.get("text"), str)
            ]
            attachments: list[UserAttachment] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")
                if part_type == "input_image":
                    attachments.append(UserAttachment(
                        kind="image",
                        url=_validated_https_url(part.get("image_url")),
                    ))
                elif part_type == "input_file":
                    filename = part.get("filename")
                    attachments.append(UserAttachment(
                        kind="file",
                        url=_validated_https_url(part.get("file_url")),
                        filename=(
                            filename.strip()
                            if isinstance(filename, str) and filename.strip()
                            else None
                        ),
                    ))
            if len(attachments) > MAX_ATTACHMENTS:
                raise ValueError(
                    f"Se permiten como máximo {MAX_ATTACHMENTS} adjuntos por solicitud"
                )
            if parts or attachments:
                return UserInput(
                    text="\n".join(parts) if parts else DEFAULT_ATTACHMENT_QUESTION,
                    attachments=tuple(attachments),
                )
    raise ValueError("No se encontró un mensaje de usuario en input")


def extract_user_text(value: str | list[dict[str, Any]]) -> str:
    """Compatibilidad con consumidores internos que solo necesitan texto."""
    return extract_user_input(value).text
