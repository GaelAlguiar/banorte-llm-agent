from fastapi.testclient import TestClient

from cv_agent.main import create_app


def test_health_does_not_require_auth():
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "gael-cv-agent",
    }


class ReadinessAgent:
    def __init__(self, ready: bool, usage_ready: bool | None = None):
        self.retrieval = type(
            "Retrieval",
            (),
            {"ready": lambda self: ready},
        )()
        self.usage_meter = None if usage_ready is None else type(
            "UsageMeter",
            (),
            {"ready": lambda self: usage_ready},
        )()


def test_readiness_reports_available_retrieval():
    response = TestClient(
        create_app(agent=ReadinessAgent(True))
    ).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "gael-cv-agent",
    }


def test_readiness_reports_unavailable_retrieval():
    response = TestClient(
        create_app(agent=ReadinessAgent(False))
    ).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "service": "gael-cv-agent",
    }


def test_readiness_reports_unavailable_usage_ledger():
    response = TestClient(
        create_app(agent=ReadinessAgent(True, usage_ready=False))
    ).get("/health/ready")

    assert response.status_code == 503
