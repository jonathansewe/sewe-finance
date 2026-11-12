"""Active sessions: list them, revoke one (SPEC 6.2 item 4, D-22).

Every query filters by the signed-in user's id. Asking for another user's
session id answers 404, exactly like an id that doesn't exist, so the API
never confirms that someone else's session exists.
"""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.db import get_session
from app.errors import ApiError
from app.models import AuthSession
from app.schemas.sessions import SessionOut
from app.security.cookies import clear_refresh_cookie
from app.security.deps import CurrentAuth, get_current_auth

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> list[SessionOut]:
    now = clock.utcnow()
    rows = db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == auth.user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_seen_at.desc())
    ).all()
    return [
        SessionOut(
            id=row.id,
            device=row.user_agent_summary,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            current=row.id == auth.session.id,
        )
        for row in rows
    ]


@router.delete("/{session_id}", status_code=204)
def revoke_session(
    session_id: uuid.UUID,
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> Response:
    row = db.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == auth.user.id,  # never another user's
            AuthSession.revoked_at.is_(None),
        )
    )
    if row is None:
        raise ApiError(404, "session_not_found", "No such session")
    row.revoked_at = clock.utcnow()
    db.commit()
    response = Response(status_code=204)
    if row.id == auth.session.id:
        clear_refresh_cookie(response)  # revoking yourself = logging out
    return response
