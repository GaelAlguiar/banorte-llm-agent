import json
import logging

from fastapi.testclient import TestClient

from cv_agent.agent.service import AgentAnswer
from cv_agent.main import create_app
from cv_agent.observability.logging import log_event


class OperationalStubAgent:
    def answer(self, question, attachments=(), reasoning_effort=None,
               max_output_tokens=None):
        return AgentAnswer(
            text="Respuesta privada que nunca debe aparecer en logs.",
            skill_name="architecture_explainer",
            evidence_ids=("documento-secreto",),
            retrieval_hit_count=3,
            source_kind_mix=("perfil", "laboral"),
            confidence_mix=("alta", "media"),
            attachment_count=1,
            attachment_kinds=("image",),
            safety_decision="allowed",
        )


def _events(caplog):
    return [json.loads(record.message) for record in caplog.records
            if record.name == "gael_cv_agent"]


def test_real_api_path_emits_content_free_operational_event(caplog):
    caplog.set_level(logging.INFO, logger="gael_cv_agent")
    client = TestClient(create_app(agent=OperationalStubAgent()))

    response = client.post(
        "/v1/responses",
        headers={"X-Request-ID": "private-correlation-id"},
        json={"input": "prompt privado con https://secret.example/path"},
    )

    assert response.status_code == 200
    event = next(item for item in _events(caplog)
                 if item["event"] == "agent_response")
    assert event["skill_name"] == "architecture_explainer"
    assert event["retrieval_hit_count"] == 3
    assert event["source_kind_mix"] == ["perfil", "laboral"]
    assert event["confidence_mix"] == ["alta", "media"]
    assert event["attachment_count"] == 1
    assert event["attachment_kinds"] == ["image"]
    assert event["safety_decision"] == "allowed"
    assert event["status"] == "success"
    assert isinstance(event["latency_ms"], float)
    serialized = "\n".join(record.message for record in caplog.records)
    for forbidden in (
        "prompt privado", "Respuesta privada", "https://", "documento-secreto",
        "private-correlation-id", "/v1/responses", "/path",
    ):
        assert forbidden not in serialized


def test_real_api_path_emits_allowlisted_error_without_exception_content(caplog):
    class FailingAgent:
        def answer(self, **kwargs):
            raise RuntimeError("secret-value https://private.example")

    caplog.set_level(logging.INFO, logger="gael_cv_agent")
    client = TestClient(create_app(agent=FailingAgent()), raise_server_exceptions=False)

    response = client.post("/v1/responses", json={"input": "private prompt"})

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "message": "El agente no pudo completar la respuesta.",
            "type": "server_error",
            "code": "agent_execution_error",
            "param": None,
        }
    }
    event = next(item for item in _events(caplog)
                 if item["event"] == "agent_response")
    assert event["status"] == "error"
    assert event["error_type"] == "agent_error"
    serialized = "\n".join(record.message for record in caplog.records)
    assert "secret-value" not in serialized
    assert "private prompt" not in serialized


def test_stream_request_provider_error_is_generic_and_content_free(caplog):
    secret = "provider-secret-id https://provider.example/private"

    class FailingAgent:
        def answer(self, **kwargs):
            raise RuntimeError(secret)

    caplog.set_level(logging.INFO, logger="gael_cv_agent")
    client = TestClient(create_app(agent=FailingAgent()))

    response = client.post(
        "/v1/responses",
        json={"input": "private streaming prompt", "stream": True},
    )

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("application/json")
    serialized = response.text + "\n" + "\n".join(
        record.message for record in caplog.records
    )
    for forbidden in (
        secret, "provider-secret-id", "provider.example", "private streaming prompt",
    ):
        assert forbidden not in serialized


def test_logger_rejects_unallowlisted_values_as_well_as_fields(caplog):
    caplog.set_level(logging.INFO, logger="gael_cv_agent")

    log_event(
        "agent_response",
        skill_name="private prompt",
        source_kind_mix=["laboral", "https://secret.example"],
        confidence_mix=["alta", "user-name"],
        attachment_kinds=["image", "/private/file"],
        safety_decision="secret-value",
        status="success",
        error_type="RuntimeError: secret-value",
        latency_ms="private",
        retrieval_hit_count=999,
    )

    event = _events(caplog)[0]
    assert event == {
        "event": "agent_response",
        "source_kind_mix": ["laboral"],
        "confidence_mix": ["alta"],
        "attachment_kinds": ["image"],
        "status": "success",
        "retrieval_hit_count": 8,
    }
