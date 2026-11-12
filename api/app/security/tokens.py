"""Access tokens (JWT), MFA tokens, and refresh tokens.

Access JWT: 15 minutes, claims `sub` (user id), `sid` (session id),
`purpose="access"`. MFA token: 5 minutes, `purpose="mfa"`, proves "password
OK, second factor still needed". Decoding pins HS256 and checks `purpose`,
so one kind can never be used as the other (D-39).
Refresh token: "<session id>.<secret>". The next secret is derived from the
current one with a server key, so a retry within the grace window gets the
same new token (D-34) without our storing any secret in plain text.
"""

import base64
import secrets
import uuid
from datetime import timedelta
from typing import Any, Literal

import jwt

from app import clock
from app.config import get_settings
from app.errors import ApiError
from app.security.hashing import keyed_hash

ALGORITHM = "HS256"
Purpose = Literal["access", "mfa"]


def _encode(claims: dict[str, Any], lifetime: timedelta) -> str:
    now = clock.utcnow()
    payload = {**claims, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    minutes = get_settings().access_token_minutes
    claims = {"sub": str(user_id), "sid": str(session_id), "purpose": "access"}
    return _encode(claims, timedelta(minutes=minutes))


def create_mfa_token(user_id: uuid.UUID) -> str:
    minutes = get_settings().mfa_token_minutes
    return _encode({"sub": str(user_id), "purpose": "mfa"}, timedelta(minutes=minutes))


def decode_token(token: str, purpose: Purpose) -> dict[str, Any]:
    """Return the claims, or raise 401 `invalid_token`. Never trusts the header's alg."""
    required = ["exp", "iat", "sub", "purpose"] + (["sid"] if purpose == "access" else [])
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],  # pinned: "none" or HS512 are rejected
            options={"require": required},
        )
        uuid.UUID(claims["sub"])
        if purpose == "access":
            uuid.UUID(claims["sid"])
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise ApiError(401, "invalid_token", "Token is invalid or expired") from exc
    if claims["purpose"] != purpose:
        raise ApiError(401, "invalid_token", "Token is invalid or expired")
    return claims


# --- Refresh tokens ---------------------------------------------------------


def new_refresh_secret() -> str:
    return secrets.token_urlsafe(32)


def format_refresh_token(session_id: uuid.UUID, secret: str) -> str:
    return f"{session_id}.{secret}"


def parse_refresh_token(token: str) -> tuple[uuid.UUID, str] | None:
    session_part, _, secret = token.partition(".")
    if not secret:
        return None
    try:
        return uuid.UUID(session_part), secret
    except ValueError:
        return None


def next_refresh_secret(session_id: uuid.UUID, secret: str) -> str:
    """Deterministic: the same current secret always derives the same next one."""
    digest = keyed_hash("refresh-next", session_id.bytes, secret)
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def refresh_secret_hash(secret: str) -> bytes:
    return keyed_hash("refresh-hash", secret)
