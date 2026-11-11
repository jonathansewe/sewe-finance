"""Recovery codes: sign in once with each, regenerate replaces them all."""

import pyotp
from fastapi.testclient import TestClient

from tests.conftest import (
    PASSWORD,
    FrozenClock,
    Outbox,
    bearer,
    enable_totp,
    signup_and_verify,
)

RECOVERY = "/api/v1/auth/recovery/verify"


def _mfa_token(client: TestClient) -> str:
    r = client.post("/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD})
    token: str = r.json()["mfa_token"]
    return token


def test_recovery_code_signs_in_once(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    _, recovery = enable_totp(client, access)

    r = client.post(RECOVERY, json={"mfa_token": _mfa_token(client), "code": recovery[0]})
    assert r.status_code == 200 and r.json()["access_token"]

    # A used recovery code is rejected.
    r = client.post(RECOVERY, json={"mfa_token": _mfa_token(client), "code": recovery[0]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "recovery_code_invalid"


def test_recovery_code_is_forgiving_about_case_and_spaces(
    client: TestClient, outbox: Outbox
) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    _, recovery = enable_totp(client, access)
    typed = recovery[3].upper().replace("-", " ")
    r = client.post(RECOVERY, json={"mfa_token": _mfa_token(client), "code": typed})
    assert r.status_code == 200


def test_made_up_recovery_code_is_rejected(client: TestClient, outbox: Outbox) -> None:
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    enable_totp(client, access)
    r = client.post(RECOVERY, json={"mfa_token": _mfa_token(client), "code": "aaaa-bbbb-cccc"})
    assert r.status_code == 400


def test_regenerate_needs_a_totp_code_and_replaces_every_code(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    frozen_clock.advance(-120)
    access = signup_and_verify(client, outbox, "jo@example.com")["access_token"]
    secret, old = enable_totp(client, access)

    r = client.post(
        "/api/v1/auth/recovery/regenerate", headers=bearer(access), json={"totp_code": "000000"}
    )
    assert r.status_code == 400  # wrong TOTP code: no new codes

    frozen_clock.advance(60)
    r = client.post(
        "/api/v1/auth/recovery/regenerate",
        headers=bearer(access),
        json={"totp_code": pyotp.TOTP(secret).at(frozen_clock.now)},
    )
    assert r.status_code == 200
    new = r.json()["recovery_codes"]
    assert len(new) == 10 and not set(new) & set(old)

    frozen_clock.advance(55)
    r = client.post(RECOVERY, json={"mfa_token": _mfa_token(client), "code": old[0]})
    assert r.status_code == 400
    r = client.post(RECOVERY, json={"mfa_token": _mfa_token(client), "code": new[0]})
    assert r.status_code == 200
