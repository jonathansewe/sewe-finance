"""Bodies for GET/PATCH /settings. M2 covers theme and language (SPEC 9).

The other user_settings columns (currency, AI provider, budget) join the
API in M8, when Settings shows them.
"""

from typing import Literal

from pydantic import BaseModel

Theme = Literal["dark", "light", "system"]
Language = Literal["en", "fr", "es"]


class SettingsOut(BaseModel):
    theme: Theme
    language: Language


class SettingsPatch(BaseModel):
    theme: Theme | None = None
    language: Language | None = None
