"""Refresh rotation, the 20 s grace window (D-34) and reuse detection (D-35)."""

from fastapi.testclient import TestClient

from app.security.tokens import new_refresh_secret, parse_refresh_token
from tests.conftest import FrozenClock, Outbox, bearer, signup_and_verify

REFRESH = "/api/v1/auth/refresh"


def _refresh(client: TestClient, token: str) -> tuple[int, dict[str, str]]:
    r = client.post(REFRESH, json={"refresh_token": token})
    body = r.json()
    return r.status_code, body.get("error", body)


def _me_status(client: TestClient, access: str) -> int:
    return client.get("/api/v1/sessions", headers=bearer(access)).status_code


def test_refresh_rotates_the_token(client: TestClient, outbox: Outbox) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")["refresh_token"]
    status, body = _refresh(client, first)
    assert status == 200
    assert body["refresh_token"] != first and body["access_token"]


def test_previous_token_within_grace_returns_the_same_new_token(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")["refresh_token"]
    _, rotated = _refresh(client, first)
    frozen_clock.advance(20)  # a second tab, 20 s later, still sends the old cookie
    status, again = _refresh(client, first)
    assert status == 200
    assert again["refresh_token"] == rotated["refresh_token"]
    # Nothing was revoked: the new token keeps working.
    assert _refresh(client, rotated["refresh_token"])[0] == 200


def test_previous_token_after_grace_counts_as_reuse_and_revokes(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")["refresh_token"]
    _, rotated = _refresh(client, first)
    frozen_clock.advance(21)
    status, error = _refresh(client, first)
    assert status == 401 and error["code"] == "refresh_reused"
    # The whole session is gone: even the newest token is refused.
    status, error = _refresh(client, rotated["refresh_token"])
    assert status == 401 and error["code"] == "refresh_invalid"


def test_reused_refresh_token_revokes_the_session(client: TestClient, outbox: Outbox) -> None:
    tokens = signup_and_verify(client, outbox, "jo@example.com")
    first = tokens["refresh_token"]
    _, second = _refresh(client, first)
    _, third = _refresh(client, second["refresh_token"])
    # `first` is two rotations old: not the immediately previous one, so no grace.
    status, error = _refresh(client, first)
    assert status == 401 and error["code"] == "refresh_reused"
    assert _me_status(client, third["access_token"]) == 401


def test_unknown_secret_for_a_real_session_does_not_revoke(
    client: TestClient, outbox: Outbox
) -> None:
    tokens = signup_and_verify(client, outbox, "jo@example.com")
    parsed = parse_refresh_token(tokens["refresh_token"])
    assert parsed is not None
    forged = f"{parsed[0]}.{new_refresh_secret()}"  # right sid, made-up secret
    status, error = _refresh(client, forged)
    assert status == 401 and error["code"] == "refresh_invalid"
    # The real user is unaffected.
    assert _refresh(client, tokens["refresh_token"])[0] == 200
    assert _me_status(client, tokens["access_token"]) == 200


def test_garbage_and_missing_tokens_are_invalid(client: TestClient) -> None:
    assert _refresh(client, "garbage")[1]["code"] == "refresh_invalid"
    r = client.post(REFRESH)
    assert r.status_code == 401 and r.json()["error"]["code"] == "refresh_invalid"


def test_browser_refresh_uses_the_cookie_not_the_body(web: TestClient, outbox: Outbox) -> None:
    web.post("/api/v1/auth/signup", json={"email": "jo@example.com", "password": "x" * 12})
    r = web.post(
        "/api/v1/auth/verify-email",
        json={"email": "jo@example.com", "code": outbox.last_code("jo@example.com")},
    )
    assert r.status_code == 200 and r.json()["refresh_token"] is None  # cookie only
    cookie = r.cookies["refresh_token"]
    # Like a browser, the client stored the cookie and sends it back by itself.
    r = web.post(REFRESH)
    assert r.status_code == 200 and r.json()["refresh_token"] is None
    assert r.cookies["refresh_token"] != cookie


def test_expired_session_cannot_refresh(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    first = signup_and_verify(client, outbox, "jo@example.com")["refresh_token"]
    frozen_clock.advance(30 * 24 * 3600 + 1)
    assert _refresh(client, first)[1]["code"] == "refresh_invalid"
