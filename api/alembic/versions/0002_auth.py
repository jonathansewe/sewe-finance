"""Auth tables: users, settings, sessions, passkeys, codes (M2).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11

Creates every table SEWE needs to sign people in (SPEC 5, 6.2). Generated
with `alembic revision --autogenerate`, then reviewed; the model files in
app/models are the source of truth, and test_migrations checks they match.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("totp_secret_enc", sa.LargeBinary(), nullable=True),
        sa.Column("totp_enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("totp_last_used_step", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "email_verification_codes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_verification_codes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_verification_codes")),
    )
    op.create_index(
        op.f("ix_email_verification_codes_user_id"),
        "email_verification_codes",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "passkeys",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False),
        sa.Column("transports", postgresql.ARRAY(sa.String(length=20)), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_passkeys_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passkeys")),
        sa.UniqueConstraint("credential_id", name=op.f("uq_passkeys_credential_id")),
    )
    op.create_index(op.f("ix_passkeys_user_id"), "passkeys", ["user_id"], unique=False)
    op.create_table(
        "recovery_codes",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.LargeBinary(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recovery_codes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recovery_codes")),
    )
    op.create_index(op.f("ix_recovery_codes_user_id"), "recovery_codes", ["user_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent_summary", sa.String(length=120), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("theme", sa.String(length=10), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("ai_provider", sa.String(length=20), nullable=False),
        sa.Column("monthly_budget_cents", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language IN ('en', 'fr', 'es')", name=op.f("ck_user_settings_language")
        ),
        sa.CheckConstraint(
            "theme IN ('dark', 'light', 'system')", name=op.f("ck_user_settings_theme")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_settings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_settings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_settings_user_id")),
    )
    op.create_table(
        "webauthn_challenges",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("purpose", sa.String(length=10), nullable=False),
        sa.Column("challenge", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_webauthn_challenges_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webauthn_challenges")),
    )
    op.create_index(
        op.f("ix_webauthn_challenges_user_id"), "webauthn_challenges", ["user_id"], unique=False
    )
    op.create_table(
        "refresh_token_history",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("secret_hash", sa.LargeBinary(), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name=op.f("fk_refresh_token_history_session_id_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_token_history")),
    )
    op.create_index(
        op.f("ix_refresh_token_history_session_id"),
        "refresh_token_history",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_token_history_session_id"), table_name="refresh_token_history")
    op.drop_table("refresh_token_history")
    op.drop_index(op.f("ix_webauthn_challenges_user_id"), table_name="webauthn_challenges")
    op.drop_table("webauthn_challenges")
    op.drop_table("user_settings")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_recovery_codes_user_id"), table_name="recovery_codes")
    op.drop_table("recovery_codes")
    op.drop_index(op.f("ix_passkeys_user_id"), table_name="passkeys")
    op.drop_table("passkeys")
    op.drop_index(
        op.f("ix_email_verification_codes_user_id"), table_name="email_verification_codes"
    )
    op.drop_table("email_verification_codes")
    op.drop_table("users")
