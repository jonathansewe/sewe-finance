"""Email verification codes and recovery codes: generate, normalise, hash.

Email codes are 6 digits (easy to type from a phone); they live 10 minutes
and allow 5 tries. Recovery codes are 12 characters from a 32-letter
alphabet with no look-alikes (60 random bits), shown once as
"xxxx-xxxx-xxxx". Both are stored only as keyed hashes (D-42), bound to
the user id, so a hash copied onto another account is useless.
"""

import secrets
import uuid

from app.security.hashing import keyed_hash

EMAIL_CODE_DIGITS = 6
RECOVERY_CODE_COUNT = 10
# Crockford base32: no i, l, o, u, so "1/l" and "0/o" can't be confused.
_RECOVERY_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
_RECOVERY_LENGTH = 12


def new_email_code() -> str:
    return str(secrets.randbelow(10**EMAIL_CODE_DIGITS)).zfill(EMAIL_CODE_DIGITS)


def email_code_hash(user_id: uuid.UUID, code: str) -> bytes:
    return keyed_hash("email-code", user_id.bytes, code.strip())


def new_recovery_codes() -> list[str]:
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(_RECOVERY_LENGTH))
        codes.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    # Accept "ABCD EFGH JKMN", "abcd-efgh-jkmn", etc.
    return "".join(ch for ch in code.lower() if ch.isalnum())


def recovery_code_hash(user_id: uuid.UUID, code: str) -> bytes:
    return keyed_hash("recovery-code", user_id.bytes, normalize_recovery_code(code))
