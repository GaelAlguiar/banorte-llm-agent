import json

from fastapi.testclient import TestClient

from cv_agent.agent.service import AgentAnswer
from cv_agent.main import create_app


class StubAgent:
    def __init__(self):
        self.calls = []

    def answer(
        self,
        question: str,
        attachments=(),
        reasoning_effort=None,
    ) -> AgentAnswer:
        assert question
        self.calls.append((question, tuple(attachments), reasoning_effort))
        return AgentAnswer(
            text="Gael es un AI Engineer con experiencia en GenAI y cloud.",
            skill_name="profile_summary",
            evidence_ids=("perfil-gael",),
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
    client = TestClient(create_app(agent=agent))

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
    question, attachments, _ = agent.calls[0]
    assert question == "Analiza esta vacante"
    assert attachments[0].kind == "image"
    assert attachments[0].url.startswith("https://files.example.com/")


def test_file_url_is_forwarded_with_filename():
    agent = StubAgent()
    client = TestClient(create_app(agent=agent))

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
    question, attachments, _ = agent.calls[0]
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
    client = TestClient(create_app(agent=StubAgent()))
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
