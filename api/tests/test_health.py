"""/health reports both the API and the database."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session
from app.main import create_app


def test_health_ok_when_database_reachable(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_503_when_database_down() -> None:
    # Port 1 has nothing listening, so every query fails fast.
    dead = create_engine(
        "postgresql+psycopg://x:x@127.0.0.1:1/x", connect_args={"connect_timeout": 1}
    )

    def dead_session() -> Iterator[Session]:
        with sessionmaker(bind=dead)() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = dead_session
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "down"}
    assert "postgresql" not in response.text  # never leak the connection string
