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
    def __init__(self, ready: bool):
        self.retrieval = type(
            "Retrieval",
            (),
            {"ready": lambda self: ready},
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
