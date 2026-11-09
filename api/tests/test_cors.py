"""CORS answers only for the configured origin, and never with a wildcard."""

from fastapi.testclient import TestClient


def test_allowed_origin_gets_cors_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:8081"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:8081"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_other_origin_gets_no_cors_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://jonathansewe.com"})
    assert "access-control-allow-origin" not in response.headers
