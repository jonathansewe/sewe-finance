"""Shared test fixtures.

Tests run against a real PostgreSQL (docker compose locally, a service
container in CI), because SQLite behaves differently in ways that hide bugs.
Point TEST_DATABASE_URL at a throwaway database; it defaults to the
docker-compose one. The schema is migrated once per run, and every table
is emptied after each test so tests can't affect each other.
Two clients: `client` behaves like the native app (no Origin header) and
`web` like the browser app (Origin: http://localhost:8081).
"""

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pyotp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://sewe:sewe@localhost:5432/sewe_test"
)
WEB_ORIGIN = "http://localhost:8081"
PASSWORD = "correct horse battery staple"  # noqa: S105 (test fixture)
API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Settings and the engine are cached; clear them so every test sees
    # the test environment, not whatever a previous test configured.
    from app.config import get_settings
    from app.db import get_engine

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("ALLOWED_ORIGINS", WEB_ORIGIN)
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    # Importing app.main already cached settings with the default database,
    # so clear the cache or Alembic would migrate the wrong one.
    get_settings.cache_clear()
    command.upgrade(Config(str(API_DIR / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def _empty_tables() -> Iterator[None]:
    yield
    from app.models import Base

    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} CASCADE"))
    engine.dispose()


@dataclass
class Outbox:
    """Stands in for the email sender: keeps messages so tests can read codes."""

    sent: list[tuple[str, str, str]] = field(default_factory=list)

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        self.sent.append((to, subject, text))

    def last_code(self, to: str) -> str:
        for recipient, _, body in reversed(self.sent):
            if recipient == to:
                match = re.search(r"\b(\d{6})\b", body)
                assert match, "no code in email"
                return match.group(1)
        raise AssertionError(f"no email to {to}")


@pytest.fixture
def outbox() -> Outbox:
    return Outbox()


@pytest.fixture
def app(outbox: Outbox) -> FastAPI:
    from app.main import create_app
    from app.services.email import get_email_sender

    application = create_app()
    application.dependency_overrides[get_email_sender] = lambda: outbox
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # https base URL so the client returns Secure cookies, like a browser.
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def web(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="https://testserver", headers={"Origin": WEB_ORIGIN})


# --- helpers -----------------------------------------------------------------


def signup_and_verify(client: TestClient, outbox: Outbox, email: str) -> dict[str, str]:
    """Create a verified account; returns the token response (native style)."""
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": PASSWORD})
    assert r.status_code == 202, r.text
    r = client.post(
        "/api/v1/auth/verify-email", json={"email": email, "code": outbox.last_code(email)}
    )
    assert r.status_code == 200, r.text
    body: dict[str, str] = r.json()
    return body


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def enable_totp(client: TestClient, access_token: str) -> tuple[str, list[str]]:
    """Turn TOTP on for the signed-in user; returns (secret, recovery codes)."""
    from app import clock

    r = client.post("/api/v1/auth/totp/setup", headers=bearer(access_token))
    assert r.status_code == 200, r.text
    secret: str = r.json()["secret"]
    r = client.post(
        "/api/v1/auth/totp/verify",
        headers=bearer(access_token),
        # The app's clock, not the real one: some tests freeze time.
        json={"code": pyotp.TOTP(secret).at(clock.utcnow())},
    )
    assert r.status_code == 200, r.text
    recovery: list[str] = r.json()["recovery_codes"]
    return secret, recovery


class FrozenClock:
    """Replaces app.clock.utcnow; move time with `advance(seconds)`."""

    def __init__(self) -> None:
        from app import clock

        self.now = clock.utcnow()

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self.now += timedelta(seconds=seconds)


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> FrozenClock:
    from app import clock

    frozen = FrozenClock()
    monkeypatch.setattr(clock, "utcnow", lambda: frozen.now)
    return frozen
