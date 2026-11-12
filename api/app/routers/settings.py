"""The signed-in user's preferences: GET and PATCH /settings.

Theme and language follow the account from M2 on, so they're the same on
every device (SPEC 9). Before sign-in, the app keeps them on the device.
The row is created at signup; `_settings_for` also creates it if missing,
so an older account can never get a 500 here.
"""

from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User, UserSettings
from app.schemas.settings import Language, SettingsOut, SettingsPatch, Theme
from app.security.deps import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_for(db: Session, user: User) -> UserSettings:
    row = db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if row is None:
        row = UserSettings(user_id=user.id, theme="system", language="en")
        db.add(row)
        db.commit()
    return row


def _out(row: UserSettings) -> SettingsOut:
    return SettingsOut(theme=cast(Theme, row.theme), language=cast(Language, row.language))


@router.get("", response_model=SettingsOut)
def get_settings(
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> SettingsOut:
    return _out(_settings_for(db, user))


@router.patch("", response_model=SettingsOut)
def patch_settings(
    body: SettingsPatch,
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> SettingsOut:
    row = _settings_for(db, user)
    if body.theme is not None:
        row.theme = body.theme
    if body.language is not None:
        row.language = body.language
    db.commit()
    return _out(row)
