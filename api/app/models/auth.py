"""Tables for sign-in state: sessions, refresh history, passkeys, codes.

`sessions` is one row per login (browser or app); its id is the `sid` in
every access token (D-18). Secrets are never stored as plain text: refresh
secrets, email codes and recovery codes are stored as keyed hashes
(security/hashing.py), so a leaked database can't be used to sign in.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TableMixin


def _user_fk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)


class AuthSession(TableMixin, Base):
    # Named AuthSession in Python so it can't be confused with a database session.
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = _user_fk()
    refresh_token_hash: Mapped[bytes] = mapped_column(LargeBinary)
    # When the current refresh secret was issued; the grace window (D-34)
    # is measured from here.
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_agent_summary: Mapped[str] = mapped_column(String(120))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshTokenHistory(TableMixin, Base):
    """Every refresh secret that was rotated out. Seeing one again = reuse (D-35)."""

    __tablename__ = "refresh_token_history"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    secret_hash: Mapped[bytes] = mapped_column(LargeBinary)
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Passkey(TableMixin, Base):
    __tablename__ = "passkeys"

    user_id: Mapped[uuid.UUID] = _user_fk()
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list)
    label: Mapped[str] = mapped_column(String(80))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecoveryCode(TableMixin, Base):
    __tablename__ = "recovery_codes"

    user_id: Mapped[uuid.UUID] = _user_fk()
    code_hash: Mapped[bytes] = mapped_column(LargeBinary)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailVerificationCode(TableMixin, Base):
    __tablename__ = "email_verification_codes"

    user_id: Mapped[uuid.UUID] = _user_fk()
    code_hash: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebAuthnChallenge(TableMixin, Base):
    """A one-time passkey challenge. Used once, then marked used_at."""

    __tablename__ = "webauthn_challenges"

    # Null for a login challenge: the user isn't known until the passkey answers.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(10))  # "register" | "login"
    challenge: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
