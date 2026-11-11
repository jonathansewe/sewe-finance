"""The `users` and `user_settings` tables.

A user row holds who you are and how you prove it: the password hash and
the encrypted TOTP secret. Preferences live in `user_settings` (one row per
user), so that changing the theme never touches the security columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TableMixin


class User(TableMixin, Base):
    __tablename__ = "users"

    # Stored trimmed and lowercased, so "Jo@X.com" and "jo@x.com" are one account.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_name: Mapped[str | None] = mapped_column(String(80))
    # AES-256-GCM ciphertext (security/encryption.py). Set by /totp/setup;
    # TOTP is only on once /totp/verify confirms a code (totp_enabled_at).
    totp_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Highest 30-second step already accepted: replay guard (D-41).
    totp_last_used_step: Mapped[int | None] = mapped_column(BigInteger)


class UserSettings(TableMixin, Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("theme IN ('dark', 'light', 'system')", name="theme"),
        CheckConstraint("language IN ('en', 'fr', 'es')", name="language"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    theme: Mapped[str] = mapped_column(String(10), default="system")
    language: Mapped[str] = mapped_column(String(2), default="en")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    ai_provider: Mapped[str] = mapped_column(String(20), default="sewe")
    monthly_budget_cents: Mapped[int | None] = mapped_column(BigInteger)
