"""CORS answers only for the configured origin, and never with a wildcard."""

from fastapi.testclient import TestClient


def test_allowed_origin_gets_cors_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:8081"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:8081"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_other_origin_gets_no_cors_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://jonathansewe.com"})
    assert "access-control-allow-origin" not in response.headers


def test_preflight_from_the_app_is_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8081"


def test_preflight_from_another_origin_is_refused(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
