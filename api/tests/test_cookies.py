"""Every Set-Cookie the API can emit has the exact attributes of D-17/D-43.

Each flow below runs as the browser app. Every Set-Cookie header it gets
must be HttpOnly, Secure, SameSite=Strict, Path=/api/v1/auth/refresh, and
must have no Domain attribute (host-only cookie). test_passkeys adds the
passkey login to this list.
"""

import time
from typing import Any

import pyotp
from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, Outbox, bearer


def assert_refresh_cookie_rules(response: Any) -> list[str]:
    headers = response.headers.get_list("set-cookie")
    for header in headers:
        parts = [p.strip().lower() for p in header.split(";")]
        name = parts[0].split("=", 1)[0]
        attrs = set(parts[1:])
        assert name == "refresh_token", header
        assert "httponly" in attrs, header
        assert "secure" in attrs, header
        assert "samesite=strict" in attrs, header
        assert "path=/api/v1/auth/refresh" in attrs, header
        assert not any(a.startswith("domain") for a in attrs), header
        assert "domain=" not in header.lower(), header
    return headers


def _web_signup(web: TestClient, outbox: Outbox, email: str) -> Any:
    web.post("/api/v1/auth/signup", json={"email": email, "password": PASSWORD})
    return web.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": outbox.last_code(email)}
    )


def test_every_auth_flow_sets_only_rule_abiding_cookies(web: TestClient, outbox: Outbox) -> None:
    seen: list[str] = []

    # verify-email
    r = _web_signup(web, outbox, "jo@example.com")
    seen += assert_refresh_cookie_rules(r)
    access = r.json()["access_token"]

    # refresh (success)
    r = web.post("/api/v1/auth/refresh")
    seen += assert_refresh_cookie_rules(r)

    # login (no TOTP yet)
    r = web.post("/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD})
    seen += assert_refresh_cookie_rules(r)

    # TOTP on, then totp/verify and recovery/verify logins
    secret = web.post("/api/v1/auth/totp/setup", headers=bearer(access)).json()["secret"]
    recovery = web.post(
        "/api/v1/auth/totp/verify",
        headers=bearer(access),
        json={"code": pyotp.TOTP(secret).now()},
    ).json()["recovery_codes"]
    mfa = web.post(
        "/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD}
    ).json()["mfa_token"]
    r = web.post("/api/v1/auth/recovery/verify", json={"mfa_token": mfa, "code": recovery[0]})
    seen += assert_refresh_cookie_rules(r)
    access = r.json()["access_token"]

    # logout clears the cookie, still without Domain
    r = web.post("/api/v1/auth/logout", headers=bearer(access))
    seen += assert_refresh_cookie_rules(r)

    # a failed refresh clears it too
    web.cookies.set("refresh_token", "garbage", domain="testserver", path="/api/v1/auth/refresh")
    r = web.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    seen += assert_refresh_cookie_rules(r)

    assert len(seen) == 6  # every flow above really set a cookie


def test_totp_login_cookie(web: TestClient, outbox: Outbox) -> None:
    access = _web_signup(web, outbox, "jo@example.com").json()["access_token"]
    secret = web.post("/api/v1/auth/totp/setup", headers=bearer(access)).json()["secret"]
    web.post(
        "/api/v1/auth/totp/verify",
        headers=bearer(access),
        json={"code": pyotp.TOTP(secret).now()},
    )
    mfa = web.post(
        "/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD}
    ).json()["mfa_token"]
    # Next step's code: the current one was just used to enable TOTP.
    code = pyotp.TOTP(secret).at(time.time() + 30)
    r = web.post("/api/v1/auth/totp/verify", json={"mfa_token": mfa, "code": code})
    assert r.status_code == 200, r.text
    assert len(assert_refresh_cookie_rules(r)) == 1


def test_revoking_your_own_session_clears_the_cookie(web: TestClient, outbox: Outbox) -> None:
    access = _web_signup(web, outbox, "jo@example.com").json()["access_token"]
    sessions = web.get("/api/v1/sessions", headers=bearer(access)).json()
    r = web.delete(f"/api/v1/sessions/{sessions[0]['id']}", headers=bearer(access))
    assert r.status_code == 204
    assert len(assert_refresh_cookie_rules(r)) == 1


def test_native_clients_get_no_cookie_at_all(client: TestClient, outbox: Outbox) -> None:
    client.post("/api/v1/auth/signup", json={"email": "jo@example.com", "password": PASSWORD})
    r = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "jo@example.com", "code": outbox.last_code("jo@example.com")},
    )
    assert r.headers.get_list("set-cookie") == []
    assert r.json()["refresh_token"]
