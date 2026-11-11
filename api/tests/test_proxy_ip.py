"""Rate limits key on the IP uvicorn trusts, never a raw X-Forwarded-For (D-36).

These tests wrap the app in uvicorn's own ProxyHeadersMiddleware, exactly
as `uvicorn --proxy-headers --forwarded-allow-ips=...` does in production,
and send login attempts from different peers.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

PROXY = "10.1.2.3"  # stands in for Render's load balancer


def _client(app: FastAPI, peer: str) -> TestClient:
    wrapped = ProxyHeadersMiddleware(app, trusted_hosts=PROXY)  # type: ignore[arg-type]
    return TestClient(wrapped, base_url="https://testserver", client=(peer, 40000))  # type: ignore[arg-type]


def _login(client: TestClient, i: int, forwarded_for: str) -> int:
    # A different unknown email each time, so only the per-IP limit can trip.
    return client.post(
        "/api/v1/auth/login",
        json={"email": f"user{i}@example.com", "password": "wrong password!"},
        headers={"X-Forwarded-For": forwarded_for},
    ).status_code


def test_spoofed_header_from_an_untrusted_peer_is_ignored(app: FastAPI) -> None:
    attacker = _client(app, "203.0.113.7")
    # Each request claims a new IP; all must still count against 203.0.113.7.
    statuses = [_login(attacker, i, f"198.51.100.{i}") for i in range(6)]
    assert statuses == [401] * 5 + [429]


def test_trusted_proxy_passes_the_real_client_ip(app: FastAPI) -> None:
    proxy = _client(app, PROXY)
    # Six different real users behind the same proxy: nobody is limited.
    statuses = [_login(proxy, i, f"198.51.100.{i}") for i in range(6)]
    assert statuses == [401] * 6


def test_a_client_cannot_prepend_fake_ips_through_the_proxy(app: FastAPI) -> None:
    proxy = _client(app, PROXY)
    # The client writes a fake entry; the proxy appends the real address.
    # uvicorn takes the right-most untrusted entry: the real one.
    statuses = [_login(proxy, i, f"192.0.2.{i}, 203.0.113.7") for i in range(6)]
    assert statuses == [401] * 5 + [429]


def test_without_proxy_trust_everyone_behind_the_proxy_shares_one_ip(app: FastAPI) -> None:
    # Why production refuses FORWARDED_ALLOW_IPS=127.0.0.1 (test_config): if
    # the proxy isn't trusted, five users lock out the sixth.
    untrusting = TestClient(
        ProxyHeadersMiddleware(app, trusted_hosts="127.0.0.1"),  # type: ignore[arg-type]
        base_url="https://testserver",
        client=(PROXY, 40000),
    )
    statuses = [_login(untrusting, i, f"198.51.100.{i}") for i in range(6)]
    assert statuses[-1] == 429
