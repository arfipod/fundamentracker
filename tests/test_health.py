from fastapi.testclient import TestClient

from api import app


def test_health_live():
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
