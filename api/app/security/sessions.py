"""Login sessions: start one, rotate its refresh token, issue tokens.

A session is one row in `sessions`; its id is the `sid` in access tokens.
`rotate_refresh_token` implements D-34 and D-35:
- the current secret → rotate (store the old hash in history, issue the next);
- the *previous* secret within 20 s → return the same next token again
  (two tabs refreshing at once must not log the user out);
- any other rotated-out secret → someone replayed a stolen token: revoke;
- a secret we never issued → 401, but the session stays alive.
"""

import uuid
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import clock
from app.config import get_settings
from app.errors import ApiError
from app.models import AuthSession, RefreshTokenHistory, User
from app.schemas.auth import TokenResponse
from app.security import tokens
from app.security.cookies import is_browser, set_refresh_cookie
from app.security.hashing import constant_time_equal

_BROWSERS = [
    ("Edg/", "Edge"),
    ("Firefox/", "Firefox"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
]
_SYSTEMS = [
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Windows", "Windows"),
    ("Mac OS X", "macOS"),
    ("Linux", "Linux"),
]


def summarize_user_agent(user_agent: str | None) -> str:
    """'Chrome on Windows': enough to recognise a session, no fingerprint."""
    ua = user_agent or ""
    if "Expo" in ua or "okhttp" in ua or "CFNetwork" in ua:
        browser = "SEWE app"
    else:
        browser = next((name for marker, name in _BROWSERS if marker in ua), "")
    system = next((name for marker, name in _SYSTEMS if marker in ua), "")
    if browser and system:
        return f"{browser} on {system}"
    return browser or system or "Unknown device"


def start_session(db: Session, user: User, request: Request) -> tuple[AuthSession, str]:
    """Create a session row and commit. Returns it and its first refresh token."""
    now = clock.utcnow()
    secret = tokens.new_refresh_secret()
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token_hash=tokens.refresh_secret_hash(secret),
        rotated_at=now,
        user_agent_summary=summarize_user_agent(request.headers.get("user-agent"))[:120],
        last_seen_at=now,
        expires_at=now + timedelta(days=get_settings().refresh_token_days),
    )
    db.add(session)
    db.commit()
    return session, tokens.format_refresh_token(session.id, secret)


def issue_tokens(
    request: Request, response: Response, session: AuthSession, refresh_token: str
) -> TokenResponse:
    """Access token in the body; refresh token as a cookie (web) or in the body (native)."""
    access = tokens.create_access_token(session.user_id, session.id)
    expires_in = get_settings().access_token_minutes * 60
    if is_browser(request):
        set_refresh_cookie(response, refresh_token)
        return TokenResponse(access_token=access, expires_in=expires_in)
    return TokenResponse(access_token=access, expires_in=expires_in, refresh_token=refresh_token)


def _invalid() -> ApiError:
    return ApiError(401, "refresh_invalid", "Refresh token is invalid or expired")


def rotate_refresh_token(db: Session, presented: str) -> tuple[AuthSession, str]:
    parsed = tokens.parse_refresh_token(presented)
    if parsed is None:
        raise _invalid()
    session_id, secret = parsed
    now = clock.utcnow()
    session = db.get(AuthSession, session_id)
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise _invalid()

    presented_hash = tokens.refresh_secret_hash(secret)
    next_secret = tokens.next_refresh_secret(session_id, secret)
    next_hash = tokens.refresh_secret_hash(next_secret)

    if constant_time_equal(presented_hash, session.refresh_token_hash):
        # Conditional UPDATE: if another request rotated this same secret a
        # moment ago, 0 rows change and we fall through to the grace path.
        result = db.execute(
            update(AuthSession)
            .where(
                AuthSession.id == session_id,
                AuthSession.refresh_token_hash == presented_hash,
                AuthSession.revoked_at.is_(None),
            )
            .values(
                refresh_token_hash=next_hash,
                rotated_at=now,
                last_seen_at=now,
                expires_at=now + timedelta(days=get_settings().refresh_token_days),
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1:  # type: ignore[attr-defined]
            db.add(
                RefreshTokenHistory(
                    session_id=session_id, secret_hash=presented_hash, rotated_at=now
                )
            )
            db.commit()
            db.refresh(session)
            return session, tokens.format_refresh_token(session_id, next_secret)
        db.rollback()
        db.refresh(session)

    # Grace (D-34): the previous secret, presented again shortly after it was
    # rotated, gets the same next token back. Nothing is changed.
    grace = timedelta(seconds=get_settings().refresh_grace_seconds)
    if constant_time_equal(next_hash, session.refresh_token_hash) and (
        now - session.rotated_at <= grace
    ):
        return session, tokens.format_refresh_token(session_id, next_secret)

    # Reuse (D-35): only a secret we really issued and rotated out revokes.
    old_hashes = db.scalars(
        select(RefreshTokenHistory.secret_hash).where(RefreshTokenHistory.session_id == session_id)
    ).all()
    if any(constant_time_equal(presented_hash, old) for old in old_hashes):
        session.revoked_at = now
        db.commit()
        raise ApiError(401, "refresh_reused", "Refresh token was already used; session revoked")
    raise _invalid()
