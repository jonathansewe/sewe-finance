"""Alembic reaches the latest revision, and the migrations match the models."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.models import Base
from tests.conftest import TEST_DATABASE_URL

API_DIR = Path(__file__).resolve().parents[1]


def test_upgrade_head_reaches_latest_revision() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with create_engine(TEST_DATABASE_URL).connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0002"


def test_models_and_migrations_agree() -> None:
    # If someone edits a model but forgets the migration, this lists the gap.
    with create_engine(TEST_DATABASE_URL).connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
