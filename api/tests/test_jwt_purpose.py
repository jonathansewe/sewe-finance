"""JWTs: algorithm pinned to HS256, and `purpose` keeps token kinds apart (D-39)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.errors import ApiError
from app.security import tokens


def _claims(**extra: object) -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "sub": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "purpose": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **extra,
    }


def test_access_token_round_trip() -> None:
    user, sid = uuid.uuid4(), uuid.uuid4()
    claims = tokens.decode_token(tokens.create_access_token(user, sid), "access")
    assert claims["sub"] == str(user) and claims["sid"] == str(sid)


def test_mfa_token_is_not_an_access_token() -> None:
    with pytest.raises(ApiError) as err:
        tokens.decode_token(tokens.create_mfa_token(uuid.uuid4()), "access")
    assert err.value.code == "invalid_token"


def test_access_token_is_not_an_mfa_token() -> None:
    access = tokens.create_access_token(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(ApiError):
        tokens.decode_token(access, "mfa")


def test_alg_none_is_rejected() -> None:
    forged = jwt.encode(_claims(), key=None, algorithm="none")
    with pytest.raises(ApiError):
        tokens.decode_token(forged, "access")


# PyJWT warns that our key is short for HS512; signing with HS512 is the attack.
@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
def test_other_hmac_algorithm_is_rejected_even_with_the_right_key() -> None:
    forged = jwt.encode(_claims(), get_settings().jwt_secret, algorithm="HS512")
    with pytest.raises(ApiError):
        tokens.decode_token(forged, "access")


def test_wrong_key_and_expired_tokens_are_rejected() -> None:
    wrong_key = jwt.encode(_claims(), "another-secret-of-sufficient-length!", algorithm="HS256")
    expired = jwt.encode(
        _claims(exp=datetime.now(UTC) - timedelta(seconds=1)),
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    for token in (wrong_key, expired):
        with pytest.raises(ApiError):
            tokens.decode_token(token, "access")


@pytest.mark.parametrize("missing", ["sid", "purpose", "exp", "sub"])
def test_missing_required_claim_is_rejected(missing: str) -> None:
    claims = _claims()
    del claims[missing]
    token = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    with pytest.raises(ApiError):
        tokens.decode_token(token, "access")


def test_refresh_token_format_and_derivation() -> None:
    sid = uuid.uuid4()
    secret = tokens.new_refresh_secret()
    assert tokens.parse_refresh_token(tokens.format_refresh_token(sid, secret)) == (sid, secret)
    assert tokens.parse_refresh_token("garbage") is None
    assert tokens.parse_refresh_token("not-a-uuid.secret") is None
    # Same input, same next secret; different session, different secret.
    assert tokens.next_refresh_secret(sid, secret) == tokens.next_refresh_secret(sid, secret)
    assert tokens.next_refresh_secret(sid, secret) != tokens.next_refresh_secret(
        uuid.uuid4(), secret
    )
