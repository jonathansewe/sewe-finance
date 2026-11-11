"""Web passkeys: register, sign in, user verification required (D-40)."""

from typing import Any

import pyotp
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, Outbox, bearer
from tests.soft_authenticator import SoftAuthenticator
from tests.test_cookies import assert_refresh_cookie_rules

BASE = "/api/v1/auth/passkey"


def _signed_in(web: TestClient, outbox: Outbox, email: str = "jo@example.com") -> str:
    web.post("/api/v1/auth/signup", json={"email": email, "password": PASSWORD})
    r = web.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": outbox.last_code(email)}
    )
    token: str = r.json()["access_token"]
    return token


def _register(web: TestClient, access: str, device: SoftAuthenticator, **kwargs: Any) -> Any:
    opts = web.post(f"{BASE}/register/options", headers=bearer(access)).json()
    credential = device.register(opts["options"], **kwargs)
    return web.post(
        f"{BASE}/register/verify",
        headers=bearer(access),
        json={"challenge_id": opts["challenge_id"], "credential": credential, "label": "Laptop"},
    )


def _login(web: TestClient, device: SoftAuthenticator, **kwargs: Any) -> Any:
    opts = web.post(f"{BASE}/login/options").json()
    credential = device.login(opts["options"], **kwargs)
    return web.post(
        f"{BASE}/login/verify",
        json={"challenge_id": opts["challenge_id"], "credential": credential},
    )


def test_options_require_user_verification_and_a_discoverable_key(
    web: TestClient, outbox: Outbox
) -> None:
    access = _signed_in(web, outbox)
    reg = web.post(f"{BASE}/register/options", headers=bearer(access)).json()["options"]
    assert reg["authenticatorSelection"]["userVerification"] == "required"
    assert reg["authenticatorSelection"]["residentKey"] == "required"
    assert reg["rp"]["id"] == "localhost"
    login = web.post(f"{BASE}/login/options").json()["options"]
    assert login["userVerification"] == "required"


def test_register_then_sign_in_with_the_passkey(web: TestClient, outbox: Outbox) -> None:
    access = _signed_in(web, outbox)
    device = SoftAuthenticator()
    r = _register(web, access, device)
    assert r.status_code == 201 and r.json()["label"] == "Laptop"

    r = _login(web, device)
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]
    assert len(assert_refresh_cookie_rules(r)) == 1  # passkey login, same cookie rules


def test_passkey_login_skips_totp_even_when_totp_is_on(web: TestClient, outbox: Outbox) -> None:
    access = _signed_in(web, outbox)
    secret = web.post("/api/v1/auth/totp/setup", headers=bearer(access)).json()["secret"]
    web.post(
        "/api/v1/auth/totp/verify", headers=bearer(access), json={"code": pyotp.TOTP(secret).now()}
    )
    device = SoftAuthenticator()
    _register(web, access, device)
    r = _login(web, device)
    assert r.status_code == 200 and r.json()["mfa_required"] is False


def test_registration_without_user_verification_is_rejected(
    web: TestClient, outbox: Outbox
) -> None:
    access = _signed_in(web, outbox)
    r = _register(web, access, SoftAuthenticator(), user_verified=False)
    assert r.status_code == 400 and r.json()["error"]["code"] == "passkey_invalid"


def test_login_without_user_verification_is_rejected(web: TestClient, outbox: Outbox) -> None:
    access = _signed_in(web, outbox)
    device = SoftAuthenticator()
    _register(web, access, device)
    r = _login(web, device, user_verified=False)
    assert r.status_code == 400 and r.json()["error"]["code"] == "passkey_invalid"


def test_wrong_origin_is_rejected(web: TestClient, outbox: Outbox) -> None:
    access = _signed_in(web, outbox)
    device = SoftAuthenticator()
    _register(web, access, device)
    r = _login(web, device, origin="https://jonathansewe.com")
    assert r.status_code == 400


def test_a_challenge_can_be_answered_only_once(web: TestClient, outbox: Outbox) -> None:
    access = _signed_in(web, outbox)
    device = SoftAuthenticator()
    _register(web, access, device)
    opts = web.post(f"{BASE}/login/options").json()
    body = {"challenge_id": opts["challenge_id"], "credential": device.login(opts["options"])}
    assert web.post(f"{BASE}/login/verify", json=body).status_code == 200
    body["credential"] = device.login(opts["options"])  # fresh signature, same challenge
    r = web.post(f"{BASE}/login/verify", json=body)
    assert r.status_code == 400 and r.json()["error"]["code"] == "passkey_challenge_invalid"


def test_unknown_passkey_is_rejected(web: TestClient) -> None:
    r = _login(web, SoftAuthenticator())
    assert r.status_code == 400 and r.json()["error"]["code"] == "passkey_invalid"


def test_another_users_register_challenge_cannot_be_used(web: TestClient, outbox: Outbox) -> None:
    a = _signed_in(web, outbox, "a@example.com")
    b = _signed_in(web, outbox, "b@example.com")
    opts = web.post(f"{BASE}/register/options", headers=bearer(a)).json()
    credential = SoftAuthenticator().register(opts["options"])
    r = web.post(
        f"{BASE}/register/verify",
        headers=bearer(b),
        json={"challenge_id": opts["challenge_id"], "credential": credential},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "passkey_challenge_invalid"


def test_registering_needs_sign_in(web: TestClient) -> None:
    # The web client sends an allowed Origin, so only the missing sign-in stops it.
    assert web.post(f"{BASE}/register/options").status_code == 401
