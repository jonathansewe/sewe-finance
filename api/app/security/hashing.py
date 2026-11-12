"""Keyed hashes and constant-time comparison (D-37, D-42).

Secrets we must recognise later (refresh secrets, email codes, recovery
codes) are stored as HMAC-SHA256 with a server key, never as plain text.
The key is derived from DATA_ENCRYPTION_KEY with HKDF, one sub-key per
purpose, so a hash made for one purpose can never be valid for another.
A keyed hash matters most for 6-digit codes: without the key, a leaked
hash could be reversed by trying all 1,000,000 codes.
"""

import base64
import hmac
from functools import lru_cache
from hashlib import sha256
from typing import Literal

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import get_settings

Purpose = Literal["refresh-hash", "refresh-next", "email-code", "recovery-code"]


@lru_cache
def _sub_key(master_key_b64: str, purpose: Purpose) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"sewe/" + purpose.encode())
    return hkdf.derive(base64.b64decode(master_key_b64))


def keyed_hash(purpose: Purpose, *parts: bytes | str) -> bytes:
    key = _sub_key(get_settings().data_encryption_key, purpose)
    mac = hmac.new(key, digestmod=sha256)
    for part in parts:
        data = part.encode() if isinstance(part, str) else part
        # Length prefix: ("ab", "c") and ("a", "bc") must hash differently.
        mac.update(len(data).to_bytes(4, "big"))
        mac.update(data)
    return mac.digest()


def constant_time_equal(a: bytes | str, b: bytes | str) -> bool:
    """`a == b` that takes the same time wherever the first difference is."""
    a_bytes = a.encode() if isinstance(a, str) else a
    b_bytes = b.encode() if isinstance(b, str) else b
    return hmac.compare_digest(a_bytes, b_bytes)
