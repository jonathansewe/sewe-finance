"""TOTP: setup, confirm, login with a code, replay, and `require_totp`.

TOTP codes depend on time, so these tests freeze the clock in the past
and step it forward (never past real time: PyJWT checks `iat` against
the real clock).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pyotp
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import User
from app.security.deps import require_totp
from tests.conftest import (
    PASSWORD,
    TEST_DATABASE_URL,
    FrozenClock,
    Outbox,
    bearer,
    enable_totp,
    signup_and_verify,
)


def _code(secret: str, at: datetime) -> str:
    return pyotp.TOTP(secret).at(at)


def _mfa_token(client: TestClient, email: str = "jo@example.com") -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200 and r.json()["mfa_required"] is True, r.text
    token: str = r.json()["mfa_token"]
    return token


def test_setup_returns_secret_qr_and_uri(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    r = client.post("/api/v1/auth/totp/setup", headers=bearer(access))
    body = r.json()
    assert r.status_code == 200
    assert body["otpauth_uri"].startswith("otpauth://totp/SEWE%20Finance:jo%40example.com?")
    assert body["qr_svg"].startswith("<svg")


def test_secret_is_encrypted_at_rest(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    secret = client.post("/api/v1/auth/totp/setup", headers=bearer(access)).json()["secret"]
    with Session(create_engine(TEST_DATABASE_URL)) as db:
        stored = db.scalars(select(User)).one().totp_secret_enc
    assert stored is not None and secret.encode() not in stored


def test_enable_then_login_needs_a_code(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    frozen_clock.advance(-120)
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    secret, recovery = enable_totp(client, access)
    assert len(recovery) == 10

    frozen_clock.advance(60)  # a new 30-second step
    mfa = _mfa_token(client)
    r = client.post(
        "/api/v1/auth/totp/verify",
        json={"mfa_token": mfa, "code": _code(secret, frozen_clock.now)},
    )
    assert r.status_code == 200 and r.json()["access_token"]


def test_wrong_code_is_rejected(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    enable_totp(client, access)
    mfa = _mfa_token(client)
    r = client.post("/api/v1/auth/totp/verify", json={"mfa_token": mfa, "code": "12345x"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "totp_invalid"


def test_a_code_cannot_be_replayed(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    frozen_clock.advance(-120)
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    secret, _ = enable_totp(client, access)
    frozen_clock.advance(60)
    code = _code(secret, frozen_clock.now)
    first = client.post(
        "/api/v1/auth/totp/verify", json={"mfa_token": _mfa_token(client), "code": code}
    )
    second = client.post(
        "/api/v1/auth/totp/verify", json={"mfa_token": _mfa_token(client), "code": code}
    )
    assert first.status_code == 200
    assert second.status_code == 400 and second.json()["error"]["code"] == "totp_invalid"


def test_older_step_is_refused_after_a_newer_one_was_used(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    frozen_clock.advance(-120)
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    secret, _ = enable_totp(client, access)
    frozen_clock.advance(60)
    older = _code(secret, frozen_clock.now)
    newer_time = frozen_clock.now.timestamp() + 30
    newer = pyotp.TOTP(secret).at(newer_time)  # next step, inside the +-1 window
    assert (
        client.post(
            "/api/v1/auth/totp/verify", json={"mfa_token": _mfa_token(client), "code": newer}
        ).status_code
        == 200
    )
    r = client.post(
        "/api/v1/auth/totp/verify", json={"mfa_token": _mfa_token(client), "code": older}
    )
    assert r.status_code == 400


def test_two_simultaneous_requests_with_one_code_only_one_wins(
    app: FastAPI, client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    frozen_clock.advance(-120)
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    secret, _ = enable_totp(client, access)
    frozen_clock.advance(60)
    code = _code(secret, frozen_clock.now)
    tokens = [_mfa_token(client), _mfa_token(client)]

    def attempt(mfa: str) -> int:
        with TestClient(app, base_url="https://testserver") as c:
            return c.post(
                "/api/v1/auth/totp/verify", json={"mfa_token": mfa, "code": code}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(attempt, tokens))
    assert statuses == [200, 400]


def test_mfa_token_cannot_be_used_as_bearer(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    enable_totp(client, access)
    r = client.get("/api/v1/sessions", headers=bearer(_mfa_token(client)))
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_access_token_cannot_be_used_as_mfa_token(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    enable_totp(client, access)
    r = client.post("/api/v1/auth/totp/verify", json={"mfa_token": access, "code": "123456"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_setup_twice_after_enabling_is_refused(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    enable_totp(client, access)
    r = client.post("/api/v1/auth/totp/setup", headers=bearer(access))
    assert r.status_code == 409 and r.json()["error"]["code"] == "totp_already_enabled"


def test_require_totp_blocks_until_two_factor_is_on(
    app: FastAPI, client: TestClient, outbox: Outbox
) -> None:
    @app.get("/test-only/bank-data")
    def bank_data(user: User = Depends(require_totp)) -> dict[str, str]:  # noqa: B008
        return {"ok": "yes"}

    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    r = client.get("/test-only/bank-data", headers=bearer(access))
    assert r.status_code == 403 and r.json()["error"]["code"] == "totp_required"
    enable_totp(client, access)
    assert client.get("/test-only/bank-data", headers=bearer(access)).status_code == 200
