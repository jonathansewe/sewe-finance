"""Signup and email verification: codes, expiry, tries, no account leaks."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import EmailVerificationCode, User
from tests.conftest import PASSWORD, TEST_DATABASE_URL, FrozenClock, Outbox

SIGNUP = "/api/v1/auth/signup"
VERIFY = "/api/v1/auth/verify-email"


def _signup(client: TestClient, email: str = "jo@example.com", **extra: str) -> None:
    r = client.post(SIGNUP, json={"email": email, "password": PASSWORD, **extra})
    assert r.status_code == 202, r.text
    assert r.json() == {"status": "verification_sent"}


def test_signup_emails_a_code_and_verify_starts_a_session(
    client: TestClient, outbox: Outbox
) -> None:
    _signup(client, "  Jo@Example.COM ")
    code = outbox.last_code("jo@example.com")  # stored lowercased and trimmed
    r = client.post(VERIFY, json={"email": "jo@example.com", "code": code})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]  # native client: in body


def test_email_is_sent_in_the_chosen_language(client: TestClient, outbox: Outbox) -> None:
    _signup(client, language="fr")
    assert outbox.sent[-1][1].startswith("Votre code SEWE Finance")


def test_code_is_stored_hashed_not_in_plain_text(client: TestClient, outbox: Outbox) -> None:
    _signup(client)
    code = outbox.last_code("jo@example.com")
    with Session(create_engine(TEST_DATABASE_URL)) as db:
        row = db.scalars(select(EmailVerificationCode)).one()
    assert code.encode() not in row.code_hash
    assert len(row.code_hash) == 32  # HMAC-SHA256


def test_wrong_code_then_right_code(client: TestClient, outbox: Outbox) -> None:
    _signup(client)
    code = outbox.last_code("jo@example.com")
    wrong = "000000" if code != "000000" else "111111"
    r = client.post(VERIFY, json={"email": "jo@example.com", "code": wrong})
    assert r.status_code == 400 and r.json()["error"]["code"] == "code_invalid"
    assert client.post(VERIFY, json={"email": "jo@example.com", "code": code}).status_code == 200


def test_expired_code_is_rejected(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    _signup(client)
    code = outbox.last_code("jo@example.com")
    frozen_clock.advance(10 * 60 + 1)
    r = client.post(VERIFY, json={"email": "jo@example.com", "code": code})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "code_expired"


def test_five_wrong_tries_burn_the_code(
    client: TestClient, outbox: Outbox, frozen_clock: FrozenClock
) -> None:
    _signup(client)
    code = outbox.last_code("jo@example.com")
    wrong = "000000" if code != "000000" else "111111"
    for attempt in range(5):
        r = client.post(VERIFY, json={"email": "jo@example.com", "code": wrong})
        expected = "code_attempts_exceeded" if attempt == 4 else "code_invalid"
        assert r.json()["error"]["code"] == expected
        frozen_clock.advance(13)  # stay under the 5-per-minute rate limit
    r = client.post(VERIFY, json={"email": "jo@example.com", "code": code})
    assert r.json()["error"]["code"] == "code_attempts_exceeded"


def test_signing_up_again_sends_a_new_code_and_kills_the_old_one(
    client: TestClient, outbox: Outbox
) -> None:
    _signup(client)
    first = outbox.last_code("jo@example.com")
    _signup(client)
    second = outbox.last_code("jo@example.com")
    if first != second:
        r = client.post(VERIFY, json={"email": "jo@example.com", "code": first})
        assert r.json()["error"]["code"] == "code_invalid"
    assert client.post(VERIFY, json={"email": "jo@example.com", "code": second}).status_code == 200


def test_signup_for_a_verified_email_looks_identical_and_sends_nothing(
    client: TestClient, outbox: Outbox
) -> None:
    _signup(client)
    code = outbox.last_code("jo@example.com")
    client.post(VERIFY, json={"email": "jo@example.com", "code": code})
    sent_before = len(outbox.sent)
    r = client.post(SIGNUP, json={"email": "jo@example.com", "password": "another password"})
    assert r.status_code == 202 and r.json() == {"status": "verification_sent"}
    assert len(outbox.sent) == sent_before
    # And the real owner's password still works.
    r = client.post("/api/v1/auth/login", json={"email": "jo@example.com", "password": PASSWORD})
    assert r.status_code == 200


def test_a_used_code_cannot_verify_twice(client: TestClient, outbox: Outbox) -> None:
    _signup(client)
    code = outbox.last_code("jo@example.com")
    assert client.post(VERIFY, json={"email": "jo@example.com", "code": code}).status_code == 200
    r = client.post(VERIFY, json={"email": "jo@example.com", "code": code})
    assert r.status_code == 400


def test_validation_errors_use_the_error_shape_and_never_echo_the_password(
    client: TestClient,
) -> None:
    r = client.post(SIGNUP, json={"email": "not-an-email", "password": "short-pass"})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "validation_error"
    assert "short-pass" not in r.text and "email" in error["message"]


def test_signup_codes_per_email_are_capped(client: TestClient, frozen_clock: FrozenClock) -> None:
    for _ in range(3):
        _signup(client)
        frozen_clock.advance(15)
    r = client.post(SIGNUP, json={"email": "jo@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["retry-after"]) > 0


def test_unverified_user_is_created_with_settings(client: TestClient) -> None:
    _signup(client, language="es")
    with Session(create_engine(TEST_DATABASE_URL)) as db:
        user = db.scalars(select(User)).one()
        assert user.email_verified_at is None
        assert user.password_hash.startswith("$argon2id$")
