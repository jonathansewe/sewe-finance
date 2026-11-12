"""SQLAlchemy tables (SPEC 5).

`Base.metadata` lists every table; Alembic compares it with the database.
Every table gets `id` (UUID), `created_at` and `updated_at` from
`TableMixin`. The model modules are imported at the bottom so that
importing `app.models` always registers all tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Predictable constraint names, so migrations can refer to them.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class TableMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


from app.models.auth import (  # noqa: E402
    AuthSession,
    EmailVerificationCode,
    Passkey,
    RecoveryCode,
    RefreshTokenHistory,
    WebAuthnChallenge,
)
from app.models.user import User, UserSettings  # noqa: E402

__all__ = [
    "AuthSession",
    "Base",
    "EmailVerificationCode",
    "Passkey",
    "RecoveryCode",
    "RefreshTokenHistory",
    "TableMixin",
    "User",
    "UserSettings",
    "WebAuthnChallenge",
]
