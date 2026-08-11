from fastapi.testclient import TestClient

from cv_agent.main import create_app


def test_health_does_not_require_auth():
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "gael-cv-agent",
    }
