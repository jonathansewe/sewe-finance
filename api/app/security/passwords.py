"""Password hashing with argon2id (SPEC 6.2).

argon2 is deliberately slow and memory-hungry, so a stolen hash is costly
to guess. `verify_dummy` runs the same work for an email that has no
account, so a login's response time doesn't reveal which emails exist (D-38).
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# argon2-cffi's defaults are argon2id with the RFC 9106 "low memory" profile.
_hasher = PasswordHasher()

# Hash of a password nobody knows, computed once at import.
_DUMMY_HASH = _hasher.hash("sewe-dummy-password-for-equal-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_dummy(password: str) -> None:
    """Spend the same time as a real check, for an unknown email (D-38)."""
    verify_password(_DUMMY_HASH, password)


def needs_rehash(password_hash: str) -> bool:
    # True when argon2's recommended cost has changed since this hash was made.
    return _hasher.check_needs_rehash(password_hash)
