"""Web passkeys: register one, then sign in with it (SPEC 6.2 item 3).

Each ceremony is two calls: /options returns a one-time challenge, the
browser asks the authenticator to sign it, /verify checks the answer with
py_webauthn. A passkey sign-in counts as both factors (something you have,
unlocked by something you are or know), so user verification is
*required* on registration and login (D-40). Challenges live 5 minutes and
are consumed by a conditional UPDATE, so each can be answered once (D-41).
Login uses discoverable credentials: no email is typed first.
"""

import json
import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app import clock
from app.config import get_settings
from app.db import get_session
from app.errors import ApiError
from app.models import Passkey, User, WebAuthnChallenge
from app.schemas.auth import TokenResponse
from app.schemas.passkeys import (
    PasskeyLoginVerifyRequest,
    PasskeyOptionsResponse,
    PasskeyOut,
    PasskeyRegisterVerifyRequest,
)
from app.security.deps import CurrentAuth, get_current_auth
from app.security.rate_limit import limit_attempts
from app.security.sessions import issue_tokens, start_session

router = APIRouter(prefix="/auth/passkey", tags=["passkeys"])
log = logging.getLogger("sewe.auth")
CHALLENGE_LIFETIME = timedelta(minutes=5)
_KNOWN_TRANSPORTS = {t.value for t in AuthenticatorTransport}


def _save_challenge(
    db: Session, purpose: str, challenge: bytes, user_id: uuid.UUID | None
) -> uuid.UUID:
    row = WebAuthnChallenge(
        user_id=user_id,
        purpose=purpose,
        challenge=challenge,
        expires_at=clock.utcnow() + CHALLENGE_LIFETIME,
    )
    db.add(row)
    db.commit()
    return row.id


def _consume_challenge(
    db: Session, challenge_id: uuid.UUID, purpose: str, user_id: uuid.UUID | None
) -> bytes:
    """Mark the challenge used and return it, or raise 400. Works once only."""
    conditions = [
        WebAuthnChallenge.id == challenge_id,
        WebAuthnChallenge.purpose == purpose,
        WebAuthnChallenge.used_at.is_(None),
        WebAuthnChallenge.expires_at > clock.utcnow(),
    ]
    if user_id is not None:
        conditions.append(WebAuthnChallenge.user_id == user_id)
    challenge: bytes | None = db.scalar(
        update(WebAuthnChallenge)
        .where(*conditions)
        .values(used_at=clock.utcnow())
        .returning(WebAuthnChallenge.challenge)
    )
    db.commit()
    if challenge is None:
        raise ApiError(400, "passkey_challenge_invalid", "Start again: that request expired")
    return challenge


def _invalid_passkey() -> ApiError:
    return ApiError(400, "passkey_invalid", "That passkey couldn't be verified")


@router.post("/register/options", response_model=PasskeyOptionsResponse)
def register_options(
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> PasskeyOptionsResponse:
    settings = get_settings()
    user = auth.user
    existing = db.scalars(select(Passkey.credential_id).where(Passkey.user_id == user.id)).all()
    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=user.id.bytes,  # opaque handle, not the email
        user_name=user.email,
        user_display_name=user.display_name or user.email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,  # discoverable: no email at login
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in existing],
    )
    challenge_id = _save_challenge(db, "register", options.challenge, user.id)
    return PasskeyOptionsResponse(
        challenge_id=challenge_id, options=json.loads(options_to_json(options))
    )


@router.post("/register/verify", response_model=PasskeyOut, status_code=201)
def register_verify(
    body: PasskeyRegisterVerifyRequest,
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> PasskeyOut:
    settings = get_settings()
    challenge = _consume_challenge(db, body.challenge_id, "register", auth.user.id)
    try:
        verified = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            require_user_verification=True,  # D-40
        )
    except InvalidRegistrationResponse as exc:
        log.info("passkey.register_failed")
        raise _invalid_passkey() from exc

    transports = body.credential.get("response", {}).get("transports", [])
    passkey = Passkey(
        user_id=auth.user.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=[t for t in transports if t in _KNOWN_TRANSPORTS],
        label=body.label,
    )
    db.add(passkey)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "passkey_exists", "This passkey is already registered") from exc
    log.info("passkey.registered")
    return PasskeyOut(id=passkey.id, label=passkey.label)


@router.post("/login/options", response_model=PasskeyOptionsResponse)
def login_options(
    request: Request,
    db: Session = Depends(get_session),  # noqa: B008
) -> PasskeyOptionsResponse:
    limit_attempts(request, "passkey", None)
    options = generate_authentication_options(
        rp_id=get_settings().webauthn_rp_id,
        user_verification=UserVerificationRequirement.REQUIRED,  # D-40
    )
    challenge_id = _save_challenge(db, "login", options.challenge, None)
    return PasskeyOptionsResponse(
        challenge_id=challenge_id, options=json.loads(options_to_json(options))
    )


@router.post("/login/verify", response_model=TokenResponse)
def login_verify(
    body: PasskeyLoginVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    limit_attempts(request, "passkey", None)
    settings = get_settings()
    challenge = _consume_challenge(db, body.challenge_id, "login", None)
    try:
        credential_id = base64url_to_bytes(str(body.credential.get("rawId", "")))
    except ValueError as exc:
        raise _invalid_passkey() from exc
    passkey = db.scalar(select(Passkey).where(Passkey.credential_id == credential_id))
    if passkey is None:
        raise _invalid_passkey()
    try:
        verified = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=True,  # D-40
        )
    except InvalidAuthenticationResponse as exc:
        log.info("passkey.login_failed")
        raise _invalid_passkey() from exc

    user = db.get(User, passkey.user_id)
    if user is None or user.email_verified_at is None:
        raise _invalid_passkey()
    passkey.sign_count = verified.new_sign_count
    passkey.last_used_at = clock.utcnow()
    db.commit()
    session, refresh = start_session(db, user, request)
    log.info("login.ok_passkey")
    return issue_tokens(request, response, session, refresh)
