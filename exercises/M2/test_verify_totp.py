"""Tests for the M2 exercise. By default they run against YOUR file
(my_verify_totp.py). CI sets SOLUTION=reference to run the same tests
against api/app/security/totp.py, which proves the tests are right.
"""

import os
import secrets
import sys
from base64 import b32encode
from pathlib import Path

import pyotp
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "api"))

if os.environ.get("SOLUTION") == "reference":
    from app.security.totp import verify_totp
else:
    from my_verify_totp import verify_totp  # type: ignore[no-redef]

# RFC 6238 Appendix B: the ASCII secret "12345678901234567890" (SHA-1),
# with the 8-digit answers cut to their last 6 digits.
RFC_SECRET = b32encode(b"12345678901234567890").decode()
RFC_VECTORS = [
    (59, "287082"),
    (1111111109, "081804"),
    (1111111111, "050471"),
    (1234567890, "005924"),
    (2000000000, "279037"),
    (20000000000, "353130"),
]


@pytest.mark.parametrize(("at_time", "code"), RFC_VECTORS)
def test_rfc_6238_vectors(at_time: int, code: str) -> None:
    assert verify_totp(RFC_SECRET, code, at_time)


def test_one_step_either_side_is_accepted() -> None:
    # "287082" belongs to step 1 (seconds 30-59).
    assert verify_totp(RFC_SECRET, "287082", 30)  # same step
    assert verify_totp(RFC_SECRET, "287082", 0)  # code is one step ahead
    assert verify_totp(RFC_SECRET, "287082", 89)  # code is one step behind


def test_two_steps_away_is_rejected() -> None:
    assert not verify_totp(RFC_SECRET, "287082", 90)  # step 3
    assert not verify_totp(RFC_SECRET, "287082", 2000)


def test_wrong_code_is_rejected() -> None:
    assert not verify_totp(RFC_SECRET, "287083", 59)


@pytest.mark.parametrize(
    "bad_code",
    ["", "28708", "2870821", "28708a", "287-082", "２８７０８２", "      "],
)
def test_malformed_codes_are_false(bad_code: str) -> None:
    assert verify_totp(RFC_SECRET, bad_code, 59) is False


def test_spaces_inside_the_code_are_ignored() -> None:
    assert verify_totp(RFC_SECRET, "287 082", 59)


def test_secret_in_lowercase_with_spaces_and_no_padding() -> None:
    messy = " ".join(RFC_SECRET.lower().rstrip("=")[i : i + 4] for i in range(0, 32, 4))
    assert verify_totp(messy, "287082", 59)


def test_secret_that_is_not_base32_raises() -> None:
    with pytest.raises(ValueError):
        verify_totp("not base32 at all!", "287082", 59)


def test_agrees_with_pyotp_on_random_secrets() -> None:
    for _ in range(50):
        secret = b32encode(secrets.token_bytes(20)).decode()
        at_time = secrets.randbelow(4_000_000_000)
        assert verify_totp(secret, pyotp.TOTP(secret).at(at_time), at_time)
