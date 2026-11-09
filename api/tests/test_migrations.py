"""Alembic can upgrade an empty database to the latest revision."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.conftest import TEST_DATABASE_URL

API_DIR = Path(__file__).resolve().parents[1]


def test_upgrade_head_reaches_latest_revision() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with create_engine(TEST_DATABASE_URL).connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0001"
