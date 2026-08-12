from dataclasses import dataclass
import ipaddress
from pathlib import PurePosixPath
import re
import socket
from typing import Any, Literal, Mapping, Protocol
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field

from cv_agent.attachments.parley import content_matches_declared_type


class CreateResponseRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = "gael-cv-agent"
    input: str | list[dict[str, Any]]
    stream: bool = False
    previous_response_id: str | None = None
    instructions: str | None = None
    max_output_tokens: int | None = Field(default=None, ge=256)
    reasoning: "ReasoningOptions | None" = None


class ReasoningOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effort: Literal["low", "medium", "high"]


@dataclass(frozen=True)
class UserAttachment:
    kind: Literal["image", "file"]
    url: str | None
    filename: str | None = None
    data: bytes | None = None
    mime_type: str | None = None


@dataclass(frozen=True)
class UserInput:
    text: str
    attachments: tuple[UserAttachment, ...] = ()


DEFAULT_ATTACHMENT_QUESTION = (
    "Analiza el archivo o imagen y relaciónalo con el perfil profesional de Gael."
)
MAX_ATTACHMENTS = 4
MAX_ATTACHMENT_FILENAME_LENGTH = 128
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_INTERNAL_SUFFIXES = (
    ".internal", ".localhost", ".local", ".lan", ".home", ".corp",
)
_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})
_FILE_EXTENSIONS = frozenset({".pdf", ".txt", ".md", ".docx"})
_IMAGE_MIME_TYPES = frozenset({
    "image/png", "image/jpeg", "image/webp", "image/gif",
})
_FILE_MIME_TYPES = frozenset({
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})
_PARLEY_FILE_REFERENCE = re.compile(
    r"^parley-file:(file_[a-z0-9]{8,64})$"
)


class AttachmentResolver(Protocol):
    def resolve(self, file_id: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class AttachmentPolicy:
    max_attachments: int = MAX_ATTACHMENTS
    trusted_hosts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.max_attachments <= MAX_ATTACHMENTS:
            raise ValueError(
                f"max_attachments debe estar entre 0 y {MAX_ATTACHMENTS}"
            )
        normalized = tuple(host.strip().lower().rstrip(".") for host in self.trusted_hosts)
        if any(not _is_public_fqdn(host) for host in normalized):
            raise ValueError("La lista de hosts de adjuntos contiene un host inválido")
        object.__setattr__(self, "trusted_hosts", normalized)


def _is_public_fqdn(hostname: str) -> bool:
    if not hostname or len(hostname) > 253 or hostname.endswith("."):
        return False
    if "." not in hostname or hostname.endswith(_INTERNAL_SUFFIXES):
        return False
    if not hostname.isascii():
        return False
    return all(_HOST_LABEL.fullmatch(label) for label in hostname.split("."))


def _validated_https_url(value: Any, policy: AttachmentPolicy) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("El adjunto debe incluir una URL HTTPS")
    url = value.strip()
    if any(character.isspace() or ord(character) < 32 for character in url):
        raise ValueError("La URL HTTPS del adjunto contiene caracteres inválidos")
    if "\\" in url:
        raise ValueError("La URL HTTPS del adjunto contiene caracteres inválidos")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("Los adjuntos deben usar una URL HTTPS válida") from error
    if parsed.scheme != "https" or not hostname:
        raise ValueError("Los adjuntos deben usar una URL HTTPS válida")
    if parsed.username or parsed.password:
        raise ValueError("La URL HTTPS del adjunto no debe contener credenciales")
    if "%" in parsed.netloc:
        raise ValueError("La URL HTTPS del adjunto contiene un host codificado")
    if port not in (None, 443):
        raise ValueError("La URL HTTPS del adjunto solo puede usar el puerto 443")
    normalized_host = hostname.lower()
    try:
        socket.inet_aton(normalized_host)
    except OSError:
        pass
    else:
        raise ValueError("La URL del adjunto debe usar un FQDN público, no una IP")
    try:
        ipaddress.ip_address(normalized_host)
    except ValueError:
        if not _is_public_fqdn(normalized_host):
            raise ValueError("El host del adjunto debe ser un FQDN público")
    else:
        raise ValueError("La URL del adjunto debe usar un FQDN público, no una IP")
    if not policy.trusted_hosts:
        raise ValueError("No hay hosts de adjuntos autorizados en la configuración")
    if not any(
        normalized_host == trusted_host
        or normalized_host.endswith(f".{trusted_host}")
        for trusted_host in policy.trusted_hosts
    ):
        raise ValueError("El host del adjunto no está autorizado")
    return url


def _validated_filename(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("El nombre del adjunto es inválido")
    filename = value.strip()
    if len(filename) > MAX_ATTACHMENT_FILENAME_LENGTH:
        raise ValueError(
            f"El nombre del adjunto excede {MAX_ATTACHMENT_FILENAME_LENGTH} caracteres"
        )
    if filename != PurePosixPath(filename).name or any(
        character in filename for character in ("\\", "\x00")
    ):
        raise ValueError("El nombre del adjunto es inválido")
    return filename


def _validate_attachment_type(
    *, kind: Literal["image", "file"], url: str | None, filename: str | None,
    mime_hints: tuple[Any, ...],
) -> None:
    allowed_extensions = _IMAGE_EXTENSIONS if kind == "image" else _FILE_EXTENSIONS
    allowed_mime_types = _IMAGE_MIME_TYPES if kind == "image" else _FILE_MIME_TYPES
    url_extension = (
        PurePosixPath(unquote(urlsplit(url).path)).suffix.lower()
        if url else ""
    )
    filename_extension = PurePosixPath(filename).suffix.lower() if filename else ""
    extensions = tuple(
        extension for extension in (url_extension, filename_extension) if extension
    )
    if any(extension not in allowed_extensions for extension in extensions):
        raise ValueError("El tipo o extensión del adjunto no está permitido")
    if len(set(extensions)) > 1:
        raise ValueError("Las extensiones declaradas para el adjunto no coinciden")
    supplied_mime_hints = tuple(hint for hint in mime_hints if hint is not None)
    if any(
        not isinstance(hint, str)
        or hint.strip().lower() not in allowed_mime_types
        for hint in supplied_mime_hints
    ):
        raise ValueError("El MIME declarado del adjunto no está permitido")
    if not extensions and not supplied_mime_hints:
        raise ValueError("El tipo o extensión del adjunto no está permitido")


def _resolved_attachment(
    value: Any,
    *,
    policy: AttachmentPolicy,
    resolver: AttachmentResolver | None,
) -> UserAttachment | None:
    if not isinstance(value, str) or not value.startswith("parley-file:"):
        return None
    match = _PARLEY_FILE_REFERENCE.fullmatch(value)
    if not match:
        raise ValueError("La referencia del archivo del portal es inválida")
    if resolver is None:
        raise ValueError(
            "No hay un resolver seguro configurado para archivos del portal"
        )
    try:
        result = resolver.resolve(match.group(1))
    except Exception as error:
        raise ValueError(
            "El archivo del portal no pudo resolverse de forma segura"
        ) from error
    if not isinstance(result, Mapping):
        raise ValueError(
            "El archivo del portal no pudo resolverse de forma segura"
        )
    raw_mime = result.get("mime_type")
    if not isinstance(raw_mime, str):
        raise ValueError(
            "El archivo del portal no pudo resolverse de forma segura"
        )
    mime_type = raw_mime.strip().lower()
    if mime_type in _IMAGE_MIME_TYPES:
        kind: Literal["image", "file"] = "image"
    elif mime_type in _FILE_MIME_TYPES:
        kind = "file"
    else:
        raise ValueError("El tipo o extensión del adjunto no está permitido")
    filename = _validated_filename(result.get("filename"))
    raw_data = result.get("data")
    raw_url = result.get("url")
    if (raw_data is None) == (raw_url is None):
        raise ValueError(
            "El archivo del portal no pudo resolverse de forma segura"
        )
    if raw_data is not None:
        if not isinstance(raw_data, bytes) or not raw_data:
            raise ValueError(
                "El archivo del portal no pudo resolverse de forma segura"
            )
        url = None
        data = raw_data
        if not content_matches_declared_type(mime_type, data):
            raise ValueError("El contenido del archivo no coincide con su tipo")
    else:
        url = _validated_https_url(raw_url, policy)
        data = None
    _validate_attachment_type(
        kind=kind,
        url=url,
        filename=filename,
        mime_hints=(mime_type,),
    )
    return UserAttachment(
        kind=kind,
        url=url,
        filename=filename,
        data=data,
        mime_type=mime_type,
    )


def extract_user_input(
    value: str | list[dict[str, Any]],
    policy: AttachmentPolicy | None = None,
    resolver: AttachmentResolver | None = None,
) -> UserInput:
    active_policy = policy or AttachmentPolicy()
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
            attachment_part_count = sum(
                1
                for part in content
                if isinstance(part, dict)
                and part.get("type") in {"input_image", "input_file"}
            )
            if attachment_part_count > active_policy.max_attachments:
                noun = (
                    "adjunto" if active_policy.max_attachments == 1
                    else "adjuntos"
                )
                raise ValueError(
                    f"Se permiten como máximo {active_policy.max_attachments} "
                    f"{noun} por solicitud"
                )
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")
                if part_type == "input_image":
                    resolved = _resolved_attachment(
                        part.get("image_url"),
                        policy=active_policy,
                        resolver=resolver,
                    )
                    if resolved is not None:
                        attachments.append(resolved)
                        continue
                    url = _validated_https_url(part.get("image_url"), active_policy)
                    _validate_attachment_type(
                        kind="image", url=url, filename=None,
                        mime_hints=tuple(
                            part.get(key)
                            for key in ("mime_type", "media_type", "content_type")
                        ),
                    )
                    attachments.append(UserAttachment(
                        kind="image",
                        url=url,
                    ))
                elif part_type == "input_file":
                    resolved = _resolved_attachment(
                        part.get("file_url"),
                        policy=active_policy,
                        resolver=resolver,
                    )
                    if resolved is not None:
                        attachments.append(resolved)
                        continue
                    filename = _validated_filename(part.get("filename"))
                    url = _validated_https_url(part.get("file_url"), active_policy)
                    _validate_attachment_type(
                        kind="file", url=url, filename=filename,
                        mime_hints=tuple(
                            part.get(key)
                            for key in ("mime_type", "media_type", "content_type")
                        ),
                    )
                    attachments.append(UserAttachment(
                        kind="file",
                        url=url,
                        filename=filename,
                    ))
            if len(attachments) > active_policy.max_attachments:
                noun = "adjunto" if active_policy.max_attachments == 1 else "adjuntos"
                raise ValueError(
                    f"Se permiten como máximo {active_policy.max_attachments} {noun} por solicitud"
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
