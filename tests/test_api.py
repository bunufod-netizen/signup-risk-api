from fastapi.testclient import TestClient
from app.main import app

def test_check_validation_and_response(monkeypatch):
    with TestClient(app) as client:
        assert client.post("/check", json={"email": "bad"}).json()["valid_format"] is False
        assert client.post("/check", json={}).status_code == 422

def test_bulk_limit():
    with TestClient(app) as client:
        response = client.post("/bulk-check", json={"emails": ["a@example.com"] * 101})
        assert response.status_code == 422


def test_gateway_secret_is_optional_then_enforced(monkeypatch):
    with TestClient(app) as client:
        assert client.post("/check", json={"email": "bad"}).status_code == 200
        monkeypatch.setattr("app.main.settings.rapidapi_proxy_secret", "gateway-secret")
        assert client.get("/health").status_code == 200
        assert client.post("/check", json={"email": "bad"}).status_code == 401
        assert client.post("/check", json={"email": "bad"}, headers={"X-RapidAPI-Proxy-Secret": "wrong"}).status_code == 401
        assert client.post("/check", json={"email": "bad"}, headers={"X-RapidAPI-Proxy-Secret": "gateway-secret"}).status_code == 200


def test_request_body_limit(monkeypatch):
    monkeypatch.setattr("app.main.settings.max_request_body_bytes", 10)
    with TestClient(app) as client:
        response = client.post("/check", content='{"email":"long@example.com"}', headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_root_metadata():
    with TestClient(app) as client:
        assert client.get("/").json() == {"name": "Signup Risk API", "version": "1.0.0", "status": "online", "docs": "/docs"}
