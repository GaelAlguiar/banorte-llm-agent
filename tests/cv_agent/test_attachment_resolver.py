from pathlib import Path
import socket

import httpx
import pytest

from cv_agent.attachments.parley import ParleyFileResolver


PUBLIC_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


def _resolver(handler, **overrides):
    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    )
    values = {
        "base_url": "https://portal.example.com/reto-ia/api/files",
        "bearer_token": "portal-file-secret",
        "client": client,
        "resolve_addresses": lambda host, port: PUBLIC_DNS,
    }
    values.update(overrides)
    return ParleyFileResolver(**values)


def test_resolver_downloads_exact_file_with_dedicated_bearer():
    fixture = Path("tests/fixtures/vacancy.png").read_bytes()

    def handler(request):
        assert str(request.url) == (
            "https://93.184.216.34/reto-ia/api/files/"
            "file_abcdefghijk123456789mnopq"
        )
        assert request.headers["host"] == "portal.example.com"
        assert request.extensions["sni_hostname"] == "portal.example.com"
        assert request.headers["authorization"] == "Bearer portal-file-secret"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(
            200,
            headers={
                "content-type": "image/png",
                "content-length": str(len(fixture)),
                "content-disposition": 'attachment; filename="arquitectura.png"',
            },
            content=fixture,
        )

    result = _resolver(handler).resolve("file_abcdefghijk123456789mnopq")

    assert result == {
        "data": fixture,
        "filename": "arquitectura.png",
        "mime_type": "image/png",
    }


def test_resolver_supports_pdf_metadata_from_actual_challenge_shape():
    fixture = Path("tests/fixtures/vacancy.pdf").read_bytes()

    result = _resolver(lambda request: httpx.Response(
        200,
        headers={
            "content-type": "application/pdf; charset=binary",
            "content-disposition": "attachment; filename*=UTF-8''vacante%20ia.pdf",
        },
        content=fixture,
    )).resolve("file_0123456789abcdefghijklmn")

    assert result["data"] == fixture
    assert result["filename"] == "vacante ia.pdf"
    assert result["mime_type"] == "application/pdf"


@pytest.mark.parametrize("file_id", [
    "file_short",
    "file_UPPERCASE1234",
    "file_abcdefgh/secret",
    "file_abcdefgh?next=private",
    "file_abcdefgh%2fsecret",
])
def test_resolver_rejects_invalid_identifier_without_network(file_id):
    calls = []
    resolver = _resolver(lambda request: calls.append(request))

    with pytest.raises(ValueError, match="referencia"):
        resolver.resolve(file_id)

    assert calls == []


@pytest.mark.parametrize("base_url", [
    "http://portal.example.com/reto-ia/api/files",
    "https://127.0.0.1/reto-ia/api/files",
    "https://user:password@portal.example.com/reto-ia/api/files",
    "https://portal.example.com:8443/reto-ia/api/files",
    "https://portal.example.com/reto-ia/api/files?next=private",
    "https://portal.example.com/reto-ia/api/files#fragment",
])
def test_resolver_rejects_unsafe_base_url(base_url):
    with pytest.raises(ValueError, match="base"):
        _resolver(lambda request: None, base_url=base_url)


def test_resolver_rejects_private_dns_before_network():
    calls = []
    resolver = _resolver(
        lambda request: calls.append(request),
        resolve_addresses=lambda host, port: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )

    with pytest.raises(ValueError, match="pública"):
        resolver.resolve("file_abcdefgh12345678")

    assert calls == []


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 403, 404, 500])
def test_resolver_fails_closed_on_redirect_or_upstream_error(status):
    response_headers = {"location": "https://127.0.0.1/private"} if status < 400 else {}
    resolver = _resolver(lambda request: httpx.Response(
        status,
        headers=response_headers,
    ))

    with pytest.raises(ValueError, match="no pudo resolverse"):
        resolver.resolve("file_abcdefgh12345678")


def test_resolver_rejects_declared_or_streamed_oversize_content():
    declared = _resolver(
        lambda request: httpx.Response(
            200,
            headers={
                "content-type": "image/png",
                "content-length": "11",
            },
            content=b"ignored",
        ),
        max_file_bytes=10,
    )
    streamed = _resolver(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"a" * 11,
        ),
        max_file_bytes=10,
    )

    with pytest.raises(ValueError, match="tamaño"):
        declared.resolve("file_abcdefgh12345678")
    with pytest.raises(ValueError, match="tamaño"):
        streamed.resolve("file_abcdefgh12345678")


@pytest.mark.parametrize(("mime_type", "content"), [
    ("image/png", b"not-a-png"),
    ("application/pdf", b"not-a-pdf"),
    ("image/svg+xml", b"<svg></svg>"),
    ("application/zip", b"PK\x03\x04"),
])
def test_resolver_rejects_spoofed_or_unsupported_content(mime_type, content):
    resolver = _resolver(lambda request: httpx.Response(
        200,
        headers={"content-type": mime_type},
        content=content,
    ))

    with pytest.raises(ValueError, match="tipo|contenido"):
        resolver.resolve("file_abcdefgh12345678")


def test_resolver_rejects_unexpected_content_encoding():
    resolver = _resolver(lambda request: httpx.Response(
        200,
        headers={
            "content-type": "text/plain",
            "content-encoding": "gzip",
        },
        content=b"compressed",
    ))

    with pytest.raises(ValueError, match="codificación|no pudo resolverse"):
        resolver.resolve("file_abcdefgh12345678")
