"""FastAPI dependencies that answer "who is calling?".

`get_current_auth` reads the Bearer access token, then loads its session
row and refuses it if revoked or expired. That database check on every
request is what makes logout and "Revoke" work immediately instead of
after the 15-minute token expires (D-18). `require_totp` guards routes
that touch bank data (SPEC 6.2 item 2), starting with imports in M3.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import clock
from app.db import get_session
from app.errors import ApiError
from app.models import AuthSession, User
from app.security.tokens import decode_token

_bearer = HTTPBearer(auto_error=False)
_LAST_SEEN_EVERY = timedelta(minutes=1)  # don't write on every request


@dataclass
class CurrentAuth:
    user: User
    session: AuthSession


def get_current_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> CurrentAuth:
    if credentials is None:
        raise ApiError(401, "not_authenticated", "Sign in first")
    claims = decode_token(credentials.credentials, "access")
    now = clock.utcnow()
    session = db.get(AuthSession, uuid.UUID(claims["sid"]))
    if (
        session is None
        or str(session.user_id) != claims["sub"]
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise ApiError(401, "session_revoked", "This session has ended; sign in again")
    user = db.get(User, session.user_id)
    if user is None:
        raise ApiError(401, "session_revoked", "This session has ended; sign in again")
    if now - session.last_seen_at > _LAST_SEEN_EVERY:
        session.last_seen_at = now
        db.commit()
    return CurrentAuth(user=user, session=session)


def get_current_user(auth: CurrentAuth = Depends(get_current_auth)) -> User:  # noqa: B008
    return auth.user


def require_totp(user: User = Depends(get_current_user)) -> User:  # noqa: B008
    if user.totp_enabled_at is None:
        raise ApiError(403, "totp_required", "Turn on two-factor authentication first")
    return user
