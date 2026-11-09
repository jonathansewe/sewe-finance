"""Shared test fixtures.

Tests run against a real PostgreSQL (docker compose locally, a service
container in CI), because SQLite behaves differently in ways that hide bugs.
Point TEST_DATABASE_URL at a throwaway database; it defaults to the
docker-compose one.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://sewe:sewe@localhost:5432/sewe_test"
)


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Settings and the engine are cached; clear them so every test sees
    # the test environment, not whatever a previous test configured.
    from app.config import get_settings
    from app.db import get_engine

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8081")
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())
