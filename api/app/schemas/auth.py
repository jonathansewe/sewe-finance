"""Request and response bodies for /auth/* (SPEC 8).

Validation happens here, before any router code runs: an email must look
like one, a password must be 10 to 128 characters (the upper bound keeps
argon2 from being fed megabytes), codes must have the right length.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Language = Literal["en", "fr", "es"]


def normalize_email(value: str) -> str:
    return value.strip().lower()


class _EmailBody(BaseModel):
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def _looks_like_email(cls, value: str) -> str:
        value = normalize_email(value)
        local, at, domain = value.partition("@")
        if not at or not local or "." not in domain or " " in value or "@" in domain:
            raise ValueError("not an email address")
        return value


class SignupRequest(_EmailBody):
    password: str = Field(min_length=10, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)
    language: Language = "en"  # the app's current language, for the email


class SignupResponse(BaseModel):
    status: Literal["verification_sent"] = "verification_sent"


class VerifyEmailRequest(_EmailBody):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginRequest(_EmailBody):
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    # Native only. Browsers send the cookie and no body.
    refresh_token: str | None = Field(default=None, max_length=200)


class TokenResponse(BaseModel):
    mfa_required: Literal[False] = False
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (not a secret)
    expires_in: int
    # Only for native clients; browsers get an HttpOnly cookie instead.
    refresh_token: str | None = None


class MfaRequiredResponse(BaseModel):
    mfa_required: Literal[True] = True
    mfa_token: str
    methods: list[Literal["totp", "recovery"]] = ["totp", "recovery"]


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=7)  # "123 456" is accepted
    # Present: second login step. Absent: confirming setup (needs Bearer).
    mfa_token: str | None = Field(default=None, max_length=2000)


class RecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]


class RecoveryVerifyRequest(BaseModel):
    mfa_token: str = Field(max_length=2000)
    code: str = Field(min_length=12, max_length=20)


class RecoveryRegenerateRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=7)
