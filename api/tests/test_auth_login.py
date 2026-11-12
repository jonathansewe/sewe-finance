"""Login: wrong password, unknown email, unverified email (D-38), rate limits."""

import pytest
from fastapi.testclient import TestClient

from app.security import passwords
from tests.conftest import PASSWORD, FrozenClock, Outbox, signup_and_verify

LOGIN = "/api/v1/auth/login"


def _login(client: TestClient, email: str, password: str) -> tuple[int, dict[str, object]]:
    r = client.post(LOGIN, json={"email": email, "password": password})
    return r.status_code, r.json()


def test_right_password_logs_in(client: TestClient, outbox: Outbox) -> None:
    signup_and_verify(client, outbox, "jo@example.com")
    status, body = _login(client, "jo@example.com", PASSWORD)
    assert status == 200 and body["mfa_required"] is False and body["access_token"]


def test_wrong_password_is_rejected(client: TestClient, outbox: Outbox) -> None:
    signup_and_verify(client, outbox, "jo@example.com")
    status, body = _login(client, "jo@example.com", "wrong password!")
    assert status == 401
    assert body == {
        "error": {"code": "invalid_credentials", "message": "Email or password is wrong"}
    }


def test_unknown_email_gets_the_same_answer_and_still_runs_argon2(
    client: TestClient, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    signup_and_verify(client, outbox, "jo@example.com")
    _, known_wrong = _login(client, "jo@example.com", "wrong password!")

    calls: list[str] = []
    real_dummy = passwords.verify_dummy
    monkeypatch.setattr(passwords, "verify_dummy", lambda pw: (calls.append(pw), real_dummy(pw)))
    status, unknown = _login(client, "nobody@example.com", "wrong password!")

    assert status == 401 and unknown == known_wrong
    assert calls == ["wrong password!"]


def test_unverified_email_with_wrong_password_looks_like_any_wrong_password(
    client: TestClient,
) -> None:
    client.post("/api/v1/auth/signup", json={"email": "new@example.com", "password": PASSWORD})
    status, body = _login(client, "new@example.com", "wrong password!")
    assert status == 401
    assert body["error"]["code"] == "invalid_credentials"  # type: ignore[index]


def test_unverified_email_with_right_password_is_told_to_verify(client: TestClient) -> None:
    client.post("/api/v1/auth/signup", json={"email": "new@example.com", "password": PASSWORD})
    status, body = _login(client, "new@example.com", PASSWORD)
    assert status == 403
    assert body["error"]["code"] == "email_not_verified"  # type: ignore[index]


def test_login_is_limited_per_account_across_ips(
    app: object, client: TestClient, outbox: Outbox
) -> None:
    signup_and_verify(client, outbox, "jo@example.com")
    for i in range(5):
        other_ip = TestClient(app, base_url="https://testserver", client=(f"10.0.0.{i}", 1000))  # type: ignore[arg-type]
        assert _login(other_ip, "jo@example.com", "wrong password!")[0] == 401
    status, body = _login(client, "jo@example.com", PASSWORD)
    assert status == 429 and body["error"]["code"] == "rate_limited"  # type: ignore[index]


def test_login_is_limited_per_ip_across_accounts(
    client: TestClient, frozen_clock: FrozenClock
) -> None:
    for i in range(5):
        assert _login(client, f"user{i}@example.com", "wrong password!")[0] == 401
    assert _login(client, "user9@example.com", "wrong password!")[0] == 429
    frozen_clock.advance(61)  # the window slides
    assert _login(client, "user9@example.com", "wrong password!")[0] == 401
