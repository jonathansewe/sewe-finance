"""The one place the API asks "what time is it?".

Code calls `clock.utcnow()` (through the module, never `from ... import`)
so a test can move time forward with monkeypatch: that is how the refresh
grace period (D-34) and code expiry are tested without sleeping.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def unix_now() -> int:
    return int(utcnow().timestamp())
