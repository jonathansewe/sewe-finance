"""Origin check on POST/PATCH/PUT/DELETE (D-16)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import WEB_ORIGIN, Outbox, bearer, signup_and_verify

REFRESH = "/api/v1/auth/refresh"


def _code(r_json: dict[str, dict[str, str]]) -> str:
    return r_json["error"]["code"]


def test_resume_site_origin_is_rejected_on_refresh(client: TestClient) -> None:
    # Same site as the API (jonathansewe.com) but not the app: must be refused.
    r = client.post(REFRESH, headers={"Origin": "https://jonathansewe.com"})
    assert r.status_code == 403 and _code(r.json()) == "origin_not_allowed"


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "https://finance.jonathansewe.com.evil.example",
        "http://localhost:8081/",  # exact match only: no trailing slash
        "http://localhost:8082",  # other port
        "https://localhost:8081",  # other scheme
        "null",  # sandboxed iframes and some redirects send this
    ],
)
def test_other_origins_are_rejected(client: TestClient, origin: str) -> None:
    r = client.post("/api/v1/auth/login", headers={"Origin": origin}, json={})
    assert r.status_code == 403 and _code(r.json()) == "origin_not_allowed"


def test_missing_origin_with_a_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set("refresh_token", "anything")
    r = client.post(REFRESH)
    assert r.status_code == 403 and _code(r.json()) == "origin_not_allowed"


def test_missing_origin_without_cookies_is_the_native_app(
    client: TestClient, outbox: Outbox
) -> None:
    tokens = signup_and_verify(client, outbox, "jo@example.com")  # no Origin at all
    r = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200


def test_allowed_origin_with_cookie_passes(web: TestClient, outbox: Outbox) -> None:
    web.post("/api/v1/auth/signup", json={"email": "jo@example.com", "password": "x" * 12})
    web.post(
        "/api/v1/auth/verify-email",
        json={"email": "jo@example.com", "code": outbox.last_code("jo@example.com")},
    )
    assert web.post(REFRESH).status_code == 200


@pytest.mark.parametrize("method", ["DELETE", "PATCH", "PUT"])
def test_every_unsafe_method_is_checked(client: TestClient, outbox: Outbox, method: str) -> None:
    tokens = signup_and_verify(client, outbox, "jo@example.com")
    r = client.request(
        method,
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000",
        headers={**bearer(tokens["access_token"]), "Origin": "https://jonathansewe.com"},
    )
    assert r.status_code == 403 and _code(r.json()) == "origin_not_allowed"


def test_safe_methods_are_not_checked(client: TestClient) -> None:
    r = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert r.status_code == 200


def test_origin_check_runs_before_the_route(app: FastAPI) -> None:
    # Even an endpoint that would 404 is refused first: nothing past the check.
    c = TestClient(app, base_url="https://testserver", headers={"Origin": "https://x.example"})
    assert c.post("/api/v1/does-not-exist").status_code == 403
    assert (
        TestClient(app, headers={"Origin": WEB_ORIGIN}).post("/api/v1/does-not-exist").status_code
        == 404
    )
