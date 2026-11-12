"""AES-256-GCM encryption for sensitive columns (SPEC 6.3).

Used for the TOTP secret, which must be readable again (we need it to check
codes), so it can't be hashed. Stored format: version byte, 12-byte random
nonce, then ciphertext + tag. The row's user id is bound in as "associated
data", so a ciphertext copied onto another user's row fails to decrypt.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

_VERSION = b"\x01"
_NONCE_BYTES = 12


def _cipher() -> AESGCM:
    key = base64.b64decode(get_settings().data_encryption_key)
    if len(key) != 32:
        raise ValueError("DATA_ENCRYPTION_KEY must be 32 bytes, base64-encoded")
    return AESGCM(key)


def encrypt(plaintext: bytes, associated_data: bytes) -> bytes:
    nonce = os.urandom(_NONCE_BYTES)  # never reuse a nonce with the same key
    return _VERSION + nonce + _cipher().encrypt(nonce, plaintext, associated_data)


def decrypt(blob: bytes, associated_data: bytes) -> bytes:
    if blob[:1] != _VERSION:
        raise ValueError("unknown ciphertext version")
    nonce = blob[1 : 1 + _NONCE_BYTES]
    # Raises cryptography.exceptions.InvalidTag if anything was tampered with.
    return _cipher().decrypt(nonce, blob[1 + _NONCE_BYTES :], associated_data)
