"""Bodies for /auth/passkey/* (web passkeys, SPEC 6.2 item 3).

`options` is the WebAuthn JSON the browser passes to navigator.credentials;
`credential` is what the browser hands back. Their exact shape is the
WebAuthn spec's, so they're plain dicts here and py_webauthn validates them.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class PasskeyOptionsResponse(BaseModel):
    challenge_id: uuid.UUID
    options: dict[str, Any]


class PasskeyRegisterVerifyRequest(BaseModel):
    challenge_id: uuid.UUID
    credential: dict[str, Any]
    label: str = Field(default="Passkey", max_length=80)


class PasskeyOut(BaseModel):
    id: uuid.UUID
    label: str


class PasskeyLoginVerifyRequest(BaseModel):
    challenge_id: uuid.UUID
    credential: dict[str, Any]
