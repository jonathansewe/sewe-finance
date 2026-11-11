"""Active sessions list + revoke (D-22), and the theme/language settings."""

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, Outbox, bearer, signup_and_verify

CHROME_WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)


def test_sessions_show_device_and_mark_this_one(client: TestClient, outbox: Outbox) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    client.post(
        "/api/v1/auth/login",
        json={"email": "jo@example.com", "password": PASSWORD},
        headers={"User-Agent": CHROME_WINDOWS},
    )
    rows = client.get("/api/v1/sessions", headers=bearer(first)).json()
    assert len(rows) == 2
    assert [r["current"] for r in rows].count(True) == 1
    assert "Chrome on Windows" in {r["device"] for r in rows}


def test_revoked_session_is_rejected_on_the_next_request(
    client: TestClient, outbox: Outbox
) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    second = client.post(
        "/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD}
    ).json()["access_token"]
    other = next(
        r for r in client.get("/api/v1/sessions", headers=bearer(first)).json() if not r["current"]
    )
    assert (
        client.delete(f"/api/v1/sessions/{other['id']}", headers=bearer(first)).status_code == 204
    )

    r = client.get("/api/v1/sessions", headers=bearer(second))
    assert r.status_code == 401 and r.json()["error"]["code"] == "session_revoked"
    # Revoked sessions drop off the list.
    assert len(client.get("/api/v1/sessions", headers=bearer(first)).json()) == 1


def test_revoking_twice_is_404(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    second = client.post(
        "/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD}
    ).json()
    other = next(
        r for r in client.get("/api/v1/sessions", headers=bearer(access)).json() if not r["current"]
    )
    client.delete(f"/api/v1/sessions/{other['id']}", headers=bearer(access))
    assert (
        client.delete(f"/api/v1/sessions/{other['id']}", headers=bearer(access)).status_code == 404
    )
    assert second["access_token"]


def test_settings_default_then_patch(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    assert client.get("/api/v1/settings", headers=bearer(access)).json() == {
        "theme": "system",
        "language": "en",
    }
    r = client.patch("/api/v1/settings", headers=bearer(access), json={"theme": "light"})
    assert r.json() == {"theme": "light", "language": "en"}


def test_settings_reject_unknown_values(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    r = client.patch("/api/v1/settings", headers=bearer(access), json={"theme": "purple"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_settings_need_sign_in(client: TestClient) -> None:
    assert client.get("/api/v1/settings").status_code == 401
