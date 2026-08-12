import json
import socket

import pytest
from fastapi.testclient import TestClient

from cv_agent.agent.service import AgentAnswer, AnswerEvidence, _public_source_url
from cv_agent.config import Settings
from cv_agent.main import create_app


class StubAgent:
    def __init__(self):
        self.calls = []

    def answer(
        self,
        question: str,
        attachments=(),
        reasoning_effort=None,
        max_output_tokens=None,
    ) -> AgentAnswer:
        assert question
        self.calls.append((
            question, tuple(attachments), reasoning_effort, max_output_tokens,
        ))
        return AgentAnswer(
            text="Gael es un AI Engineer con experiencia en GenAI y cloud.",
            skill_name="profile_summary",
            evidence_ids=("perfil-gael",),
            evidence=(AnswerEvidence(
                document_id="perfil-gael",
                chunk_id="perfil-gael--resumen",
                title="Perfil de Gael — Resumen",
                section="Resumen",
                public_url="https://example.com/gael",
                source_kind="perfil",
                evidence_level="directa",
                impact_type="confirmado",
                confidence="alta",
            ),),
        )


def test_create_response_returns_typed_output():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        json={
            "model": "gael-cv-agent",
            "input": "¿Quién es Gael?",
            "stream": False,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["object"] == "response"
    assert body["status"] == "completed"
    assert body["error"] is None
    assert body["output"][0]["type"] == "message"
    assert body["output"][0]["content"][0]["type"] == "output_text"
    assert "AI Engineer" in body["output"][0]["content"][0]["text"]
    evidence = body["evidence"]
    assert evidence[0] == {
        "document_id": "perfil-gael",
        "chunk_id": "perfil-gael--resumen",
        "title": "Perfil de Gael — Resumen",
        "section": "Resumen",
        "public_url": "https://example.com/gael",
        "source_kind": "perfil",
        "evidence_level": "directa",
        "impact_type": "confirmado",
        "confidence": "alta",
    }


def test_message_item_input_uses_last_user_text():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        json={
            "input": [
                {"role": "assistant", "content": "Hola"},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "¿Qué experiencia tiene?"}
                    ],
                },
            ]
        },
    )

    assert response.status_code == 200


def test_image_url_is_forwarded_as_an_attachment():
    agent = StubAgent()
    client = TestClient(create_app(
        settings=Settings(trusted_attachment_hosts=("example.com",)),
        agent=agent,
    ))

    response = client.post(
        "/v1/responses",
        json={
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Analiza esta vacante"},
                    {
                        "type": "input_image",
                        "image_url": "https://files.example.com/vacante.png?token=abc",
                    },
                ],
            }],
        },
    )

    assert response.status_code == 200
    question, attachments, _, _ = agent.calls[0]
    assert question == "Analiza esta vacante"
    assert attachments[0].kind == "image"
    assert attachments[0].url.startswith("https://files.example.com/")


def test_file_url_is_forwarded_with_filename():
    agent = StubAgent()
    client = TestClient(create_app(
        settings=Settings(trusted_attachment_hosts=("example.com",)),
        agent=agent,
    ))

    response = client.post(
        "/v1/responses",
        json={
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_file",
                    "file_url": "https://files.example.com/descripcion.pdf?sig=abc",
                    "filename": "descripcion.pdf",
                }],
            }],
        },
    )

    assert response.status_code == 200
    question, attachments, _, _ = agent.calls[0]
    assert question == "Analiza el archivo o imagen y relaciónalo con el perfil profesional de Gael."
    assert attachments[0].kind == "file"
    assert attachments[0].filename == "descripcion.pdf"


def test_non_https_attachment_url_is_rejected():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        json={
            "input": [{
                "role": "user",
                "content": [{
                    "type": "input_file",
                    "file_url": "http://127.0.0.1/private.txt",
                }],
            }],
        },
    )

    assert response.status_code == 400
    assert "HTTPS" in response.json()["detail"]


def test_more_than_four_attachments_is_rejected():
    client = TestClient(create_app(
        settings=Settings(trusted_attachment_hosts=("example.com",)),
        agent=StubAgent(),
    ))
    content = [
        {
            "type": "input_image",
            "image_url": f"https://files.example.com/{index}.png",
        }
        for index in range(5)
    ]

    response = client.post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": content}]},
    )

    assert response.status_code == 400
    assert "4 adjuntos" in response.json()["detail"]


@pytest.mark.parametrize("url", [
    "https://localhost/vacante.png",
    "https://service/vacante.png",
    "https://metadata.google.internal/vacante.png",
    "https://127.0.0.1/vacante.png",
    "https://10.0.0.1/vacante.png",
    "https://172.16.0.1/vacante.png",
    "https://192.168.1.1/vacante.png",
    "https://169.254.169.254/vacante.png",
    "https://0.0.0.0/vacante.png",
    "https://224.0.0.1/vacante.png",
    "https://240.0.0.1/vacante.png",
    "https://8.8.8.8/vacante.png",
    "https://127.1/vacante.png",
    "https://0177.0.0.1/vacante.png",
    "https://0x7f.0.0.1/vacante.png",
    "https://0x7f000001/vacante.png",
    "https://2130706433/vacante.png",
    "https://127.0x0.0.1/vacante.png",
    "https://[::1]/vacante.png",
    "https://[fc00::1]/vacante.png",
    "https://[fe80::1]/vacante.png",
    "https://[ff02::1]/vacante.png",
    "https://user:password@files.example.com/vacante.png",
    "https://files.example.com:invalid/vacante.png",
    "https://127%2e0%2e0%2e1/vacante.png",
    "https://files%2eexample.com/vacante.png",
    "https://files.example.com\\@127.0.0.1/vacante.png",
    "https://files.example.com./vacante.png",
])
def test_unsafe_attachment_urls_are_rejected(url):
    response = TestClient(create_app(
        settings=Settings(trusted_attachment_hosts=("example.com",)),
        agent=StubAgent(),
    )).post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": [{
            "type": "input_image", "image_url": url,
        }]}]},
    )

    assert response.status_code == 400


def test_attachment_host_allowlist_is_required_and_allows_subdomains():
    no_allowlist = TestClient(create_app(agent=StubAgent())).post(
        "/v1/responses", json={"input": [{"role": "user", "content": [{
            "type": "input_image",
            "image_url": "https://uploads.banorte.example/vacante.png",
        }]}]},
    )
    settings = Settings(
        trusted_attachment_hosts=("banorte.example",),
    )
    client = TestClient(create_app(settings=settings, agent=StubAgent()))

    denied = client.post("/v1/responses", json={"input": [{
        "role": "user", "content": [{
            "type": "input_image",
            "image_url": "https://files.example.com/vacante.png",
        }],
    }]})
    allowed = client.post("/v1/responses", json={"input": [{
        "role": "user", "content": [{
            "type": "input_image",
            "image_url": "https://uploads.banorte.example/vacante.png",
        }],
    }]})

    assert no_allowlist.status_code == 400
    assert denied.status_code == 400
    assert allowed.status_code == 200


def test_configured_attachment_limit_is_enforced():
    settings = Settings(
        max_attachments=1,
        trusted_attachment_hosts=("example.com",),
    )
    client = TestClient(create_app(settings=settings, agent=StubAgent()))
    content = [
        {"type": "input_image", "image_url": f"https://files.example.com/{index}.png"}
        for index in range(2)
    ]

    response = client.post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": content}]},
    )

    assert response.status_code == 400
    assert "1 adjunto" in response.json()["detail"]


@pytest.mark.parametrize("part", [
    {"type": "input_image", "image_url": "https://files.example.com/vacante.svg"},
    {"type": "input_image", "image_url": "https://files.example.com/vacante.png", "mime_type": "image/svg+xml"},
    {"type": "input_file", "file_url": "https://files.example.com/vacante.exe", "filename": "vacante.exe"},
    {"type": "input_file", "file_url": "https://files.example.com/vacante.zip", "filename": "vacante.zip"},
    {"type": "input_file", "file_url": "https://files.example.com/vacante.bin", "filename": "vacante.bin"},
    {"type": "input_file", "file_url": "https://files.example.com/vacante.pdf", "filename": "vacante.pdf", "mime_type": "application/zip"},
])
def test_unsupported_or_mismatched_attachment_type_is_rejected(part):
    response = TestClient(create_app(agent=StubAgent())).post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": [part]}]},
    )

    assert response.status_code == 400
    assert "adjunto" in response.json()["detail"].lower()


def test_excessive_attachment_filename_is_rejected():
    response = TestClient(create_app(agent=StubAgent())).post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": [{
            "type": "input_file",
            "file_url": "https://files.example.com/vacante.pdf",
            "filename": f"{'a' * 129}.pdf",
        }]}]},
    )

    assert response.status_code == 400
    assert "nombre" in response.json()["detail"].lower()


def test_attachment_validation_never_resolves_dns(monkeypatch):
    def unexpected_dns(*args, **kwargs):
        raise AssertionError("No debe resolverse DNS durante la solicitud")

    monkeypatch.setattr(socket, "getaddrinfo", unexpected_dns)

    response = TestClient(create_app(
        settings=Settings(trusted_attachment_hosts=("example.com",)),
        agent=StubAgent(),
    )).post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": [{
            "type": "input_image",
            "image_url": "https://signed-files.example.com/vacante.png?sig=abc",
        }]}]},
    )

    assert response.status_code == 200


@pytest.mark.parametrize("part", [
    {"type": "input_image"},
    {"type": "input_file", "filename": "vacante.pdf"},
    {
        "type": "input_file",
        "file_url": "https://files.example.com/payload.exe",
        "filename": "vacante.pdf",
    },
    {
        "type": "input_file",
        "file_url": "https://files.example.com/vacante.pdf",
        "filename": "vacante.pdf",
        "content_type": "application/zip",
    },
])
def test_missing_corrupt_or_spoofed_attachment_metadata_is_rejected(part):
    response = TestClient(create_app(agent=StubAgent())).post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": [part]}]},
    )

    assert response.status_code == 400


def test_attachment_url_is_not_persisted_in_logs_or_response(caplog):
    caplog.set_level("INFO", logger="gael_cv_agent")
    sensitive_url = "https://files.example.com/vacante.png?sig=do-not-log"

    response = TestClient(create_app(
        settings=Settings(trusted_attachment_hosts=("example.com",)),
        agent=StubAgent(),
    )).post(
        "/v1/responses",
        json={"input": [{"role": "user", "content": [{
            "type": "input_image", "image_url": sensitive_url,
        }]}]},
    )

    assert response.status_code == 200
    assert sensitive_url not in response.text
    assert "do-not-log" not in caplog.text


def test_streamed_body_over_limit_is_rejected_without_content_length():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        content=iter((b'{"input":"', b"a" * 1_048_576, b'"}')),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_streamed_body_under_limit_is_replayed_to_json_parser():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        content=iter((b'{"input":"', "¿Quién es Gael?".encode(), b'"}')),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 200


def test_configured_body_limit_accepts_boundary_and_rejects_next_byte():
    settings = Settings(max_request_body_bytes=65_536)
    client = TestClient(create_app(settings=settings, agent=StubAgent()))
    payload = b'{"input":"x"}'
    accepted_body = payload + b" " * (65_536 - len(payload))

    accepted = client.post(
        "/v1/responses",
        content=accepted_body,
        headers={"content-type": "application/json"},
    )
    rejected = client.post(
        "/v1/responses",
        content=accepted_body + b" ",
        headers={"content-type": "application/json"},
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 413
    assert rejected.json()["error"]["code"] == "request_too_large"


def test_reasoning_effort_is_forwarded_to_agent():
    agent = StubAgent()
    client = TestClient(create_app(agent=agent))

    response = client.post(
        "/v1/responses",
        json={
            "input": "Analiza la experiencia de Gael",
            "reasoning": {"effort": "medium"},
        },
    )

    assert response.status_code == 200
    assert agent.calls[0][2] == "medium"


def test_invalid_reasoning_effort_is_rejected():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        json={
            "input": "Analiza la experiencia de Gael",
            "reasoning": {"effort": "extreme"},
        },
    )

    assert response.status_code == 422


def test_streaming_response_matches_reference_event_sequence():
    client = TestClient(create_app(agent=StubAgent()))

    response = client.post(
        "/v1/responses",
        json={"input": "¿Quién es Gael?", "stream": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        line.removeprefix("event: ")
        for line in response.text.splitlines()
        if line.startswith("event: ")
    ]
    assert events == [
        "response.created",
        "response.in_progress",
        "response.output_item.added",
        "response.content_part.added",
        "response.output_text.delta",
        "response.output_text.done",
        "response.content_part.done",
        "response.output_item.done",
        "response.completed",
    ]
    data_lines = [
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]
    assert all(json.loads(line) for line in data_lines)
    assert response.text.rstrip().endswith("data: [DONE]")
    completed = json.loads(data_lines[-1])["response"]
    assert completed["evidence"][0]["chunk_id"] == (
        "perfil-gael--resumen"
    )


@pytest.mark.parametrize("stream", [False, True])
def test_max_output_tokens_is_forwarded_with_json_sse_parity(stream):
    agent = StubAgent()
    response = TestClient(create_app(agent=agent)).post(
        "/v1/responses",
        json={
            "input": "¿Quién es Gael?",
            "stream": stream,
            "max_output_tokens": 777,
        },
    )

    assert response.status_code == 200
    assert agent.calls[0][3] == 777


def test_previous_response_id_is_rejected_instead_of_ignored():
    agent = StubAgent()
    response = TestClient(create_app(agent=agent)).post(
        "/v1/responses",
        json={
            "input": "Continúa",
            "previous_response_id": "resp_platform_supplied",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "message": "previous_response_id no está soportado por este agente sin estado.",
        "type": "invalid_request_error",
        "code": "unsupported_previous_response_id",
        "param": "previous_response_id",
    }
    assert agent.calls == []


def test_output_budget_below_supported_minimum_is_rejected_not_increased():
    agent = StubAgent()
    response = TestClient(create_app(agent=agent)).post(
        "/v1/responses",
        json={"input": "¿Quién es Gael?", "max_output_tokens": 255},
    )

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "max_output_tokens"]
    assert "256" in error["msg"]
    assert agent.calls == []


def test_response_evidence_never_exposes_local_or_private_sources():
    class PrivateEvidenceAgent(StubAgent):
        def answer(self, question, attachments=(), reasoning_effort=None,
                   max_output_tokens=None):
            return AgentAnswer(
                text="Respuesta segura.",
                skill_name="profile_summary",
                evidence_ids=("perfil-gael",),
                evidence=(AnswerEvidence(
                    document_id="perfil-gael",
                    chunk_id="perfil-gael--resumen",
                    title="Perfil",
                    section=None,
                    public_url=None,
                    source_kind="perfil",
                    evidence_level="directa",
                    impact_type="confirmado",
                    confidence="alta",
                ),),
            )

    body = TestClient(create_app(agent=PrivateEvidenceAgent())).post(
        "/v1/responses", json={"input": "¿Quién es Gael?"}
    ).json()

    serialized = json.dumps(body)
    assert "/Users/" not in serialized
    assert "source_path" not in serialized
    assert "vector_score" not in serialized
    assert "score" not in serialized


def test_response_metadata_values_are_compact_strings_with_detailed_top_level_evidence():
    body = TestClient(create_app(agent=StubAgent())).post(
        "/v1/responses", json={"input": "¿Quién es Gael?"}
    ).json()

    assert body["evidence"][0]["document_id"] == "perfil-gael"
    assert all(isinstance(value, str) for value in body["metadata"].values())
    assert all(len(value) <= 512 for value in body["metadata"].values())
    assert body["metadata"]["evidence_ids"] == "perfil-gael--resumen"


def test_public_evidence_url_requires_an_authorized_domain():
    assert _public_source_url("https://enereylatam.com/proyecto") == (
        None
    )
    assert _public_source_url("https://enereylatam.com") == "https://enereylatam.com/"
    assert _public_source_url("https://www.lugramx.com/") == "https://www.lugramx.com/"
    assert _public_source_url("https://apps.apple.com/mx/app/enerey/id6736633080/") == (
        "https://apps.apple.com/mx/app/enerey/id6736633080"
    )
    for unsafe in (
        "https://intranet/path",
        "https://example.com/path",
        "https://evil.com/path",
        "https://user:pass@files.example.com/path",
        "https://enereylatam.com:8443/path",
        "https://enereylatam.com:bad/path",
        "https://enereylatam.com.evil.com/path",
        "https://ｅｎｅｒｅｙlatam.com/path",
        "https://enereylatam.com/%2e%2e/private",
        "https://apps.apple.com/mx/app/enerey/id6736633080/private",
    ):
        assert _public_source_url(unsafe) is None
