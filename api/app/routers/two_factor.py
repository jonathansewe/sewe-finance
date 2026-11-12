"""Two-factor sign-in: TOTP setup and verify, recovery codes (SPEC 6.2).

/totp/setup makes a secret (encrypted at rest) and returns its QR code.
/totp/verify does two jobs:
  - with a Bearer token and no `mfa_token`: confirm setup, turn TOTP on,
    and return 10 recovery codes (shown once);
  - with an `mfa_token` from /login: finish signing in.
/recovery/verify signs in with a recovery code instead. /recovery/regenerate
replaces all codes (needs a current TOTP code).
Every code is single-use, enforced by a conditional UPDATE (D-41).
"""

import logging
import uuid

import segno
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app import clock
from app.db import get_session
from app.errors import ApiError
from app.models import RecoveryCode, User
from app.schemas.auth import (
    RecoveryCodesResponse,
    RecoveryRegenerateRequest,
    RecoveryVerifyRequest,
    TokenResponse,
    TotpSetupResponse,
    TotpVerifyRequest,
)
from app.security import codes, encryption, totp
from app.security.deps import CurrentAuth, get_current_auth
from app.security.hashing import constant_time_equal
from app.security.rate_limit import limit_attempts
from app.security.sessions import issue_tokens, start_session
from app.security.tokens import decode_token

router = APIRouter(prefix="/auth", tags=["two-factor"])
log = logging.getLogger("sewe.auth")
_optional_bearer = HTTPBearer(auto_error=False)


def _user_from_mfa_token(db: Session, mfa_token: str) -> User:
    claims = decode_token(mfa_token, "mfa")
    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None or user.totp_enabled_at is None:
        raise ApiError(401, "invalid_token", "Token is invalid or expired")
    return user


def _consume_totp_code(db: Session, user: User, code: str) -> None:
    """Accept `code` once, or raise 400 `totp_invalid`. Leaves the change uncommitted."""
    if user.totp_secret_enc is None:
        raise ApiError(400, "totp_setup_required", "Set up two-factor first")
    secret = encryption.decrypt(user.totp_secret_enc, user.id.bytes).decode()
    step = totp.matching_step(secret, code, clock.unix_now())
    invalid = ApiError(400, "totp_invalid", "That code isn't right")
    if step is None:
        raise invalid
    # Replay guard (D-41): only one request can move the step forward, even
    # if two arrive at the same moment with the same code.
    result = db.execute(
        update(User)
        .where(
            User.id == user.id,
            or_(User.totp_last_used_step.is_(None), User.totp_last_used_step < step),
        )
        .values(totp_last_used_step=step)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise invalid


def _new_recovery_codes(db: Session, user: User) -> list[str]:
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    plain = codes.new_recovery_codes()
    db.add_all(
        RecoveryCode(user_id=user.id, code_hash=codes.recovery_code_hash(user.id, c)) for c in plain
    )
    return plain


@router.post("/totp/setup", response_model=TotpSetupResponse)
def totp_setup(
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> TotpSetupResponse:
    user = auth.user
    if user.totp_enabled_at is not None:
        raise ApiError(409, "totp_already_enabled", "Two-factor is already on")
    secret = totp.generate_secret()
    user.totp_secret_enc = encryption.encrypt(secret.encode(), user.id.bytes)
    db.commit()
    uri = totp.provisioning_uri(secret, user.email)
    qr_svg = segno.make(uri, error="m").svg_inline(scale=5, border=2)
    log.info("totp.setup_started")
    return TotpSetupResponse(secret=secret, otpauth_uri=uri, qr_svg=qr_svg)


@router.post("/totp/verify", response_model=TokenResponse | RecoveryCodesResponse)
def totp_verify(
    body: TotpVerifyRequest,
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> TokenResponse | RecoveryCodesResponse:
    if body.mfa_token is not None:
        # Second step of signing in.
        user = _user_from_mfa_token(db, body.mfa_token)
        limit_attempts(request, "totp", str(user.id))
        _consume_totp_code(db, user, body.code)
        db.commit()
        session, refresh = start_session(db, user, request)
        log.info("login.ok_totp")
        return issue_tokens(request, response, session, refresh)

    # Confirming setup: must already be signed in.
    auth = get_current_auth(credentials, db)
    user = auth.user
    limit_attempts(request, "totp", str(user.id))
    if user.totp_enabled_at is not None:
        raise ApiError(409, "totp_already_enabled", "Two-factor is already on")
    _consume_totp_code(db, user, body.code)
    db.refresh(user)
    user.totp_enabled_at = clock.utcnow()
    recovery = _new_recovery_codes(db, user)
    db.commit()
    log.info("totp.enabled")
    return RecoveryCodesResponse(recovery_codes=recovery)


@router.post("/recovery/verify", response_model=TokenResponse)
def recovery_verify(
    body: RecoveryVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    user = _user_from_mfa_token(db, body.mfa_token)
    limit_attempts(request, "recovery", str(user.id))
    presented = codes.recovery_code_hash(user.id, body.code)
    unused = db.scalars(
        select(RecoveryCode).where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
    ).all()
    # Compare against every unused code in constant time (D-37); the hash is
    # never used to look a row up.
    match: RecoveryCode | None = None
    for row in unused:
        if constant_time_equal(presented, row.code_hash) and match is None:
            match = row
    invalid = ApiError(400, "recovery_code_invalid", "That recovery code isn't valid")
    if match is None:
        raise invalid
    used = db.execute(
        update(RecoveryCode)
        .where(RecoveryCode.id == match.id, RecoveryCode.used_at.is_(None))
        .values(used_at=clock.utcnow())
    )
    if used.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise invalid
    db.commit()
    session, refresh = start_session(db, user, request)
    log.info("login.ok_recovery")
    return issue_tokens(request, response, session, refresh)


@router.post("/recovery/regenerate", response_model=RecoveryCodesResponse)
def recovery_regenerate(
    body: RecoveryRegenerateRequest,
    request: Request,
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> RecoveryCodesResponse:
    user = auth.user
    limit_attempts(request, "recovery", str(user.id))
    if user.totp_enabled_at is None:
        raise ApiError(400, "totp_setup_required", "Set up two-factor first")
    # A stolen access token alone must not be enough to mint new codes.
    _consume_totp_code(db, user, body.totp_code)
    recovery = _new_recovery_codes(db, user)
    db.commit()
    log.info("recovery.regenerated")
    return RecoveryCodesResponse(recovery_codes=recovery)
