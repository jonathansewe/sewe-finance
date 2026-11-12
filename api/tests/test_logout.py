"""Logout revokes the session named by `sid` and takes effect at once (D-18)."""

from fastapi.testclient import TestClient

from tests.conftest import Outbox, bearer, signup_and_verify


def test_logout_revokes_this_session_only(client: TestClient, outbox: Outbox) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")
    second = client.post(
        "/api/v1/auth/login",
        json={"email": "jo@example.com", "password": "correct horse battery staple"},
    ).json()

    r = client.post("/api/v1/auth/logout", headers=bearer(first["access_token"]))
    assert r.status_code == 204

    # The very next request with the old (still unexpired) access token fails.
    r = client.get("/api/v1/sessions", headers=bearer(first["access_token"]))
    assert r.status_code == 401 and r.json()["error"]["code"] == "session_revoked"
    # Its refresh token is dead too.
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 401
    # The other session is untouched.
    assert client.get("/api/v1/sessions", headers=bearer(second["access_token"])).status_code == 200


def test_logout_clears_the_cookie(client: TestClient, outbox: Outbox) -> None:
    tokens = signup_and_verify(client, outbox, "jo@example.com")
    r = client.post("/api/v1/auth/logout", headers=bearer(tokens["access_token"]))
    set_cookie = r.headers["set-cookie"].lower()
    assert set_cookie.startswith("refresh_token=")
    assert "max-age=0" in set_cookie and "path=/api/v1/auth/refresh" in set_cookie


def test_logout_needs_an_access_token(client: TestClient) -> None:
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 401 and r.json()["error"]["code"] == "not_authenticated"
