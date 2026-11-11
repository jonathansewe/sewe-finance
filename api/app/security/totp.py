"""Time-based one-time passwords (RFC 6238), written with the standard library.

An authenticator app and the server share a secret. Every 30 seconds both
compute HMAC-SHA1(secret, step number) and cut it down to 6 digits; if the
user's digits match ours, they hold the secret. We also accept the step
before and after, because phone clocks drift. This is the reference
solution for exercises/M2 (`verify_totp`).
"""

import base64
import binascii
import hmac
import secrets
import struct
from hashlib import sha1
from urllib.parse import quote, urlencode

from app.security.hashing import constant_time_equal

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1  # steps accepted on each side of "now"


def generate_secret() -> str:
    """160 random bits as base32: what authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _secret_bytes(secret: str) -> bytes:
    cleaned = secret.replace(" ", "").upper()
    padded = cleaned + "=" * (-len(cleaned) % 8)
    try:
        return base64.b32decode(padded)
    except binascii.Error as exc:
        raise ValueError("secret is not valid base32") from exc


def hotp(key: bytes, counter: int) -> str:
    """RFC 4226: HMAC the counter, then 'dynamic truncation' to DIGITS digits."""
    digest = hmac.new(key, struct.pack(">Q", counter), sha1).digest()
    offset = digest[-1] & 0x0F  # the last 4 bits pick where to read
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def code_at(secret: str, at_time: int) -> str:
    return hotp(_secret_bytes(secret), at_time // STEP_SECONDS)


def matching_step(secret: str, code: str, at_time: int) -> int | None:
    """The 30-second step `code` belongs to (within the window), or None.

    The router stores the returned step so the same code can't be used
    twice (D-41). A malformed secret raises ValueError: that's a bug, not
    a wrong guess.
    """
    key = _secret_bytes(secret)
    code = code.replace(" ", "")
    if len(code) != DIGITS or not code.isascii() or not code.isdigit():
        return None
    now_step = at_time // STEP_SECONDS
    found: int | None = None
    # Check every step in the window, even after a match, so timing doesn't
    # reveal which one matched.
    for step in range(now_step - WINDOW, now_step + WINDOW + 1):
        if constant_time_equal(hotp(key, step), code) and found is None:
            found = step
    return found


def verify_totp(secret: str, code: str, at_time: int) -> bool:
    return matching_step(secret, code, at_time) is not None


def provisioning_uri(secret: str, account_email: str, issuer: str = "SEWE Finance") -> str:
    """The otpauth:// link inside the QR code an authenticator app scans."""
    # "Issuer:account", each part escaped but the colon kept, as apps expect.
    label = f"{quote(issuer)}:{quote(account_email)}"
    query = urlencode({"secret": secret, "issuer": issuer, "digits": DIGITS, "period": 30})
    return f"otpauth://totp/{label}?{query}"
