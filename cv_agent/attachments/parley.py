from collections.abc import Callable
from email.message import Message
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx


_FILE_ID = re.compile(r"^file_[a-z0-9]{8,64}$")
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_ALLOWED_MIME_TYPES = frozenset({
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/pdf",
    "text/plain",
    "text/markdown",
})
MAX_PARLEY_FILE_BYTES = 10_485_760


def _public_base_url(value: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as error:
        raise ValueError("La URL base del resolver es inválida") from error
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or "\\" in value
        or any(character.isspace() or ord(character) < 32 for character in value)
    ):
        raise ValueError("La URL base del resolver debe ser HTTPS pública")
    if "." not in hostname or not hostname.isascii() or not all(
        _HOST_LABEL.fullmatch(label) for label in hostname.split(".")
    ):
        raise ValueError("La URL base del resolver debe usar un FQDN público")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("La URL base del resolver no puede usar una IP")
    path = parsed.path.rstrip("/")
    if not path or path == "/":
        raise ValueError("La URL base del resolver debe incluir una ruta")
    return f"https://{hostname}{path}", hostname


def _filename(headers: httpx.Headers, mime_type: str) -> str:
    disposition = headers.get("content-disposition")
    if disposition:
        message = Message()
        message["content-disposition"] = disposition
        candidate = message.get_filename()
        if candidate:
            return unquote(candidate)
    extension = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/markdown": ".md",
    }[mime_type]
    return f"adjunto{extension}"


def content_matches_declared_type(mime_type: str, data: bytes) -> bool:
    if not data:
        return False
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if mime_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if mime_type in {"text/plain", "text/markdown"}:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return b"\x00" not in data
    return False


class ParleyFileResolver:
    """Obtiene un archivo opaco desde una única ruta confiable y autenticada."""

    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str,
        max_file_bytes: int = MAX_PARLEY_FILE_BYTES,
        client: httpx.Client | None = None,
        resolve_addresses: Callable[[str, int], list[Any]] | None = None,
    ) -> None:
        self.base_url, self.hostname = _public_base_url(base_url)
        self.base_path = urlsplit(self.base_url).path
        if (
            not isinstance(bearer_token, str)
            or not bearer_token.strip()
            or len(bearer_token) > 4_096
            or any(character.isspace() or ord(character) < 32 for character in bearer_token)
        ):
            raise ValueError("El token del resolver es inválido")
        if not 1 <= max_file_bytes <= MAX_PARLEY_FILE_BYTES:
            raise ValueError(
                f"max_file_bytes debe estar entre 1 y {MAX_PARLEY_FILE_BYTES}"
            )
        self.bearer_token = bearer_token
        self.max_file_bytes = max_file_bytes
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
        )
        self.resolve_addresses = resolve_addresses or socket.getaddrinfo

    def _validated_addresses(self) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            addresses = self.resolve_addresses(self.hostname, 443)
        except OSError as error:
            raise ValueError("El host del resolver no pudo validarse") from error
        if not addresses:
            raise ValueError("El host del resolver no pudo validarse")
        try:
            ips = [ipaddress.ip_address(item[4][0]) for item in addresses]
        except (IndexError, TypeError, ValueError) as error:
            raise ValueError("El host del resolver no pudo validarse") from error
        if any(not address.is_global for address in ips):
            raise ValueError("El host del resolver debe resolver a una IP pública")
        return ips

    def resolve(
        self, file_id: str, *, max_bytes: int | None = None,
    ) -> dict[str, Any]:
        if not isinstance(file_id, str) or not _FILE_ID.fullmatch(file_id):
            raise ValueError("La referencia del archivo del portal es inválida")
        effective_max_bytes = self.max_file_bytes
        if max_bytes is not None:
            if max_bytes < 1:
                raise ValueError("El tamaño total de adjuntos excede el límite")
            effective_max_bytes = min(effective_max_bytes, max_bytes)
        addresses = self._validated_addresses()
        selected_address = addresses[0]
        address_literal = (
            f"[{selected_address.compressed}]"
            if selected_address.version == 6
            else selected_address.compressed
        )
        url = f"https://{address_literal}{self.base_path}/{file_id}"
        try:
            with self.client.stream(
                "GET",
                url,
                headers={
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Accept": ", ".join(sorted(_ALLOWED_MIME_TYPES)),
                    "Accept-Encoding": "identity",
                    "Host": self.hostname,
                },
                extensions={"sni_hostname": self.hostname},
            ) as response:
                if response.status_code != 200:
                    raise ValueError(
                        "El archivo del portal no pudo resolverse de forma segura"
                    )
                content_encoding = response.headers.get("content-encoding", "identity")
                if content_encoding.lower().strip() not in {"", "identity"}:
                    raise ValueError(
                        "La codificación del archivo del portal no está permitida"
                    )
                raw_content_type = response.headers.get("content-type", "")
                mime_type = raw_content_type.split(";", 1)[0].strip().lower()
                if mime_type not in _ALLOWED_MIME_TYPES:
                    raise ValueError("El tipo del archivo del portal no está permitido")
                raw_length = response.headers.get("content-length")
                if raw_length:
                    try:
                        declared_length = int(raw_length)
                    except ValueError as error:
                        raise ValueError(
                            "El tamaño del archivo del portal es inválido"
                        ) from error
                    if declared_length < 0 or declared_length > effective_max_bytes:
                        raise ValueError(
                            "El tamaño del archivo del portal excede el límite"
                        )
                body = bytearray()
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > effective_max_bytes:
                        raise ValueError(
                            "El tamaño del archivo del portal excede el límite"
                        )
                    body.extend(chunk)
        except ValueError:
            raise
        except httpx.HTTPError as error:
            raise ValueError(
                "El archivo del portal no pudo resolverse de forma segura"
            ) from error
        data = bytes(body)
        if not content_matches_declared_type(mime_type, data):
            raise ValueError("El contenido del archivo no coincide con su tipo")
        return {
            "data": data,
            "filename": _filename(response.headers, mime_type),
            "mime_type": mime_type,
        }
