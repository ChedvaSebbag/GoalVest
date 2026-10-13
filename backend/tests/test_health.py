from unittest.mock import patch

from app import create_app
from app.config import Config


class TestConfig(Config):
    DB_CONNECTION_STRING = ""
    OLLAMA_BASE_URL = "http://127.0.0.1:9"   # פורט סגור – נכשל מהר
    CHROMA_URL = "http://127.0.0.1:9"
    HEALTH_TIMEOUT_SECONDS = 0.5
    JWT_SECRET = "unit-test-jwt-secret-0123456789abcd"
    RATELIMIT_ENABLED = False


def test_health_returns_503_with_details_when_services_down():
    client = create_app(TestConfig).test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 503
    body = resp.get_json()
    assert set(body["checks"]) == {"database", "ollama", "chroma"}
    assert all(c["status"] == "error" for c in body["checks"].values())


def test_health_returns_200_when_all_ok():
    ok = {"status": "ok", "detail": "x"}
    with patch("app.controllers.health.check_database", return_value=ok), \
         patch("app.controllers.health.check_ollama", return_value=ok), \
         patch("app.controllers.health.check_chroma", return_value=ok):
        resp = create_app(TestConfig).test_client().get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
