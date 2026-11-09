"""Baseline: empty schema.

Revision ID: 0001
Revises:
Create Date: 2026-11-06

M1 has no tables. This revision exists so `alembic upgrade head` works from
day one and M2's first real migration has a parent to point to.
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
