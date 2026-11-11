"""Unit tests for passwords, hashing, encryption, TOTP helpers and codes."""

import uuid

import pyotp
import pytest
from cryptography.exceptions import InvalidTag

from app.security import codes, encryption, hashing, passwords, totp

# --- passwords ---------------------------------------------------------------


def test_password_round_trip_and_wrong_password() -> None:
    stored = passwords.hash_password("correct horse battery")
    assert stored.startswith("$argon2id$")
    assert passwords.verify_password(stored, "correct horse battery")
    assert not passwords.verify_password(stored, "wrong horse battery")


def test_verify_password_with_garbage_hash_is_false_not_crash() -> None:
    assert not passwords.verify_password("not-a-hash", "anything")


# --- hashing -----------------------------------------------------------------


def test_keyed_hash_separates_purposes_and_parts() -> None:
    assert hashing.keyed_hash("email-code", "123456") != hashing.keyed_hash(
        "recovery-code", "123456"
    )
    assert hashing.keyed_hash("email-code", "ab", "c") != hashing.keyed_hash(
        "email-code", "a", "bc"
    )


def test_constant_time_equal() -> None:
    assert hashing.constant_time_equal(b"abc", "abc")
    assert not hashing.constant_time_equal(b"abc", b"abd")


# --- encryption --------------------------------------------------------------


def test_encrypt_round_trip_uses_fresh_nonce() -> None:
    aad = uuid.uuid4().bytes
    a = encryption.encrypt(b"JBSWY3DPEHPK3PXP", aad)
    b = encryption.encrypt(b"JBSWY3DPEHPK3PXP", aad)
    assert a != b  # random nonce
    assert encryption.decrypt(a, aad) == b"JBSWY3DPEHPK3PXP"


def test_ciphertext_moved_to_another_user_fails() -> None:
    blob = encryption.encrypt(b"secret", uuid.uuid4().bytes)
    with pytest.raises(InvalidTag):
        encryption.decrypt(blob, uuid.uuid4().bytes)


def test_tampered_ciphertext_fails() -> None:
    aad = b"user"
    blob = bytearray(encryption.encrypt(b"secret", aad))
    blob[-1] ^= 1
    with pytest.raises(InvalidTag):
        encryption.decrypt(bytes(blob), aad)


# --- TOTP helpers (verify_totp itself: exercises/M2) --------------------------


def test_generated_secret_works_with_a_real_authenticator_library() -> None:
    secret = totp.generate_secret()
    now = 1_800_000_000
    assert totp.verify_totp(secret, pyotp.TOTP(secret).at(now), now)


def test_matching_step_reports_which_step_matched() -> None:
    secret = totp.generate_secret()
    now = 1_800_000_015
    previous = pyotp.TOTP(secret).at(now - 30)
    assert totp.matching_step(secret, previous, now) == now // 30 - 1


def test_provisioning_uri_is_understood_by_pyotp() -> None:
    secret = totp.generate_secret()
    uri = totp.provisioning_uri(secret, "jo@example.com")
    parsed = pyotp.parse_uri(uri)
    assert parsed.secret == secret
    assert parsed.issuer == "SEWE Finance"
    assert parsed.name == "jo@example.com"


# --- codes -------------------------------------------------------------------


def test_email_code_is_six_digits() -> None:
    for _ in range(50):
        code = codes.new_email_code()
        assert len(code) == 6 and code.isdigit()


def test_recovery_codes_are_unique_and_formatted() -> None:
    generated = codes.new_recovery_codes()
    assert len(generated) == 10 == len(set(generated))
    for code in generated:
        assert len(code) == 14 and code[4] == "-" and code[9] == "-"


def test_recovery_code_hash_ignores_case_and_separators_but_binds_the_user() -> None:
    user = uuid.uuid4()
    code = codes.new_recovery_codes()[0]
    spaced = code.upper().replace("-", " ")
    assert codes.recovery_code_hash(user, code) == codes.recovery_code_hash(user, spaced)
    assert codes.recovery_code_hash(user, code) != codes.recovery_code_hash(uuid.uuid4(), code)


def test_email_code_hash_binds_the_user() -> None:
    assert codes.email_code_hash(uuid.uuid4(), "123456") != codes.email_code_hash(
        uuid.uuid4(), "123456"
    )
