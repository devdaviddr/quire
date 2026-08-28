from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_version_and_database():
    body = client.get("/health").json()
    assert body["version"]
    assert "database" in body
