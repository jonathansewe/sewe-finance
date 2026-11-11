"""GET /me: who is signed in, and how their account is protected.

The app calls this after every sign-in and page reload to decide where to
go next: TOTP setup if two-factor is off, the "add a passkey" offer if the
account has none. It returns no secrets. (DELETE /me, account deletion,
arrives with Settings in M8.)
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Passkey, User
from app.security.deps import get_current_user

router = APIRouter(tags=["me"])


class MeOut(BaseModel):
    email: str
    display_name: str | None
    totp_enabled: bool
    passkey_count: int


@router.get("/me", response_model=MeOut)
def me(
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> MeOut:
    passkeys = db.scalar(select(func.count()).where(Passkey.user_id == user.id)) or 0
    return MeOut(
        email=user.email,
        display_name=user.display_name,
        totp_enabled=user.totp_enabled_at is not None,
        passkey_count=passkeys,
    )
