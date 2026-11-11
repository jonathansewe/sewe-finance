"""Sign up, verify email, log in, refresh, log out (SPEC 6.2, 8).

Flow: /signup emails a 6-digit code → /verify-email checks it and starts a
session → /login checks the password and either starts a session or, when
TOTP is on, returns an `mfa_token` for /totp/verify or /recovery/verify
(routers/two_factor.py). /refresh rotates the refresh token; /logout ends
the session named by the access token's `sid` (D-18).
Error answers never reveal whether an email has an account (D-38, D-45).
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import clock
from app.db import get_session
from app.errors import ApiError, error_body
from app.models import EmailVerificationCode, User, UserSettings
from app.schemas.auth import (
    LoginRequest,
    MfaRequiredResponse,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    VerifyEmailRequest,
)
from app.security import codes, passwords, tokens
from app.security.cookies import REFRESH_COOKIE, clear_refresh_cookie, is_browser
from app.security.deps import CurrentAuth, get_current_auth
from app.security.hashing import constant_time_equal
from app.security.rate_limit import limit_attempts, limit_custom
from app.security.sessions import issue_tokens, rotate_refresh_token, start_session
from app.services.email import EmailSender, get_email_sender
from app.services.email_messages import verification_email

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("sewe.auth")

CODE_LIFETIME = timedelta(minutes=10)
MAX_CODE_ATTEMPTS = 5
# Resend's free tier is 100 emails/day, shared with other projects (D-25).
CODES_PER_EMAIL_PER_HOUR = 3


@router.post("/signup", status_code=202, response_model=SignupResponse)
def signup(
    body: SignupRequest,
    request: Request,
    db: Session = Depends(get_session),  # noqa: B008
    sender: EmailSender = Depends(get_email_sender),  # noqa: B008
) -> SignupResponse:
    limit_attempts(request, "signup", None)
    limit_custom(request, f"signup-email:{body.email}", CODES_PER_EMAIL_PER_HOUR, 3600)
    # Hash first, every time, so all branches below take similar time.
    password_hash = passwords.hash_password(body.password)

    user = db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.email_verified_at is not None:
        # Same answer as a new signup; no email, nothing changes (D-45).
        log.info("signup.existing_verified")
        return SignupResponse()

    if user is None:
        user = User(email=body.email, password_hash=password_hash, display_name=body.display_name)
        db.add(user)
        try:
            db.flush()
        except IntegrityError:  # two signups for one new email at the same moment
            db.rollback()
            return SignupResponse()
        db.add(UserSettings(user_id=user.id, language=body.language))
    else:
        # Unverified: whoever can read the inbox decides the password, so a
        # stranger can't pre-register someone else's email and keep it.
        user.password_hash = password_hash
        user.display_name = body.display_name
        db.execute(
            update(UserSettings)
            .where(UserSettings.user_id == user.id)
            .values(language=body.language)
        )

    code = codes.new_email_code()
    db.execute(delete(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id))
    db.add(
        EmailVerificationCode(
            user_id=user.id,
            code_hash=codes.email_code_hash(user.id, code),
            expires_at=clock.utcnow() + CODE_LIFETIME,
        )
    )
    db.commit()
    subject, text = verification_email(code, body.language)
    sender.send(user.email, subject, text)
    log.info("signup.code_sent")
    return SignupResponse()


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),  # noqa: B008
) -> TokenResponse:
    limit_attempts(request, "verify-email", body.email)
    invalid = ApiError(400, "code_invalid", "That code isn't right")
    now = clock.utcnow()

    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or user.email_verified_at is not None:
        raise invalid
    row = db.scalar(select(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id))
    if row is None or row.used_at is not None:
        raise invalid
    if row.expires_at <= now:
        raise ApiError(400, "code_expired", "That code has expired; sign up again for a new one")

    # Count the attempt atomically (D-41): two parallel guesses can't both
    # slip in as attempt number 5.
    attempts = db.scalar(
        update(EmailVerificationCode)
        .where(
            EmailVerificationCode.id == row.id,
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.attempts < MAX_CODE_ATTEMPTS,
        )
        .values(attempts=EmailVerificationCode.attempts + 1)
        .returning(EmailVerificationCode.attempts)
    )
    too_many = ApiError(400, "code_attempts_exceeded", "Too many wrong codes; sign up again")
    if attempts is None:
        db.rollback()
        raise too_many
    if not constant_time_equal(codes.email_code_hash(user.id, body.code), row.code_hash):
        db.commit()
        raise too_many if attempts >= MAX_CODE_ATTEMPTS else invalid

    used = db.execute(
        update(EmailVerificationCode)
        .where(EmailVerificationCode.id == row.id, EmailVerificationCode.used_at.is_(None))
        .values(used_at=now)
    )
    if used.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise invalid
    user.email_verified_at = now
    session, refresh = start_session(db, user, request)  # commits
    log.info("email.verified")
    return issue_tokens(request, response, session, refresh)


@router.post("/login", response_model=TokenResponse | MfaRequiredResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),  # noqa: B008
) -> TokenResponse | MfaRequiredResponse:
    limit_attempts(request, "login", body.email)
    bad = ApiError(401, "invalid_credentials", "Email or password is wrong")

    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        passwords.verify_dummy(body.password)  # same cost as a real check (D-38)
        log.info("login.failed")
        raise bad
    if not passwords.verify_password(user.password_hash, body.password):
        log.info("login.failed")
        raise bad
    # Only now, with the right password, may we say the email isn't verified.
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(body.password)
        db.commit()
    if user.email_verified_at is None:
        raise ApiError(403, "email_not_verified", "Verify your email first")
    if user.totp_enabled_at is not None:
        log.info("login.mfa_required")
        return MfaRequiredResponse(mfa_token=tokens.create_mfa_token(user.id))

    session, refresh = start_session(db, user, request)
    log.info("login.ok")
    return issue_tokens(request, response, session, refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: Session = Depends(get_session),  # noqa: B008
) -> TokenResponse | JSONResponse:
    browser = is_browser(request)
    presented = request.cookies.get(REFRESH_COOKIE) if browser else (body and body.refresh_token)
    try:
        if not presented:
            raise ApiError(401, "refresh_invalid", "Refresh token is invalid or expired")
        session, new_token = rotate_refresh_token(db, presented)
    except ApiError as exc:
        log.info("refresh.failed")
        failed = JSONResponse(
            status_code=exc.status_code, content=error_body(exc.code, exc.message)
        )
        if browser:
            clear_refresh_cookie(failed)  # a dead cookie is no use to keep
        return failed
    return issue_tokens(request, response, session, new_token)


@router.post("/logout", status_code=204)
def logout(
    auth: CurrentAuth = Depends(get_current_auth),  # noqa: B008
    db: Session = Depends(get_session),  # noqa: B008
) -> Response:
    auth.session.revoked_at = clock.utcnow()
    db.commit()
    log.info("logout")
    response = Response(status_code=204)
    clear_refresh_cookie(response)
    return response
