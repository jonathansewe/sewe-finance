"""User A can never read or change user B's data (SPEC 6.3)."""

from fastapi.testclient import TestClient

from tests.conftest import Outbox, bearer, signup_and_verify


def _two_users(client: TestClient, outbox: Outbox) -> tuple[str, str]:
    a = signup_and_verify(client, outbox, "a@example.com")["access_token"]
    b = signup_and_verify(client, outbox, "b@example.com")["access_token"]
    return a, b


def test_sessions_list_shows_only_your_own(client: TestClient, outbox: Outbox) -> None:
    a, b = _two_users(client, outbox)
    a_sessions = client.get("/api/v1/sessions", headers=bearer(a)).json()
    b_sessions = client.get("/api/v1/sessions", headers=bearer(b)).json()
    assert len(a_sessions) == len(b_sessions) == 1
    assert a_sessions[0]["id"] != b_sessions[0]["id"]


def test_a_cannot_revoke_b_session(client: TestClient, outbox: Outbox) -> None:
    a, b = _two_users(client, outbox)
    b_session = client.get("/api/v1/sessions", headers=bearer(b)).json()[0]["id"]
    r = client.delete(f"/api/v1/sessions/{b_session}", headers=bearer(a))
    # 404, the same as a made-up id: no hint that the session exists.
    assert r.status_code == 404 and r.json()["error"]["code"] == "session_not_found"
    assert client.get("/api/v1/sessions", headers=bearer(b)).status_code == 200


def test_settings_are_per_user(client: TestClient, outbox: Outbox) -> None:
    a, b = _two_users(client, outbox)
    client.patch("/api/v1/settings", headers=bearer(a), json={"theme": "dark", "language": "fr"})
    assert client.get("/api/v1/settings", headers=bearer(a)).json() == {
        "theme": "dark",
        "language": "fr",
    }
    assert client.get("/api/v1/settings", headers=bearer(b)).json() == {
        "theme": "system",
        "language": "en",
    }
