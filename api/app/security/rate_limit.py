"""In-memory sliding-window rate limits (SPEC 6.2 item 7).

Each sign-in endpoint counts attempts twice: per client IP and per account.
The IP comes only from `request.client.host`, which uvicorn has already set
from X-Forwarded-For *if* the peer is a trusted proxy (FORWARDED_ALLOW_IPS).
We never read X-Forwarded-For ourselves: any client can write it (D-36).
Known limit: counters live in this process, so they reset on restart and
aren't shared between workers. Fine for one Render instance; move them to
Postgres or Redis before running more than one.
"""

import threading
from collections import deque

from fastapi import Request

from app import clock
from app.errors import ApiError

LIMIT_PER_MINUTE = 5


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        """Count one attempt for `key`, or raise 429 if it's over the limit."""
        now = clock.utcnow().timestamp()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = int(hits[0] + window_seconds - now) + 1
                raise ApiError(
                    429,
                    "rate_limited",
                    "Too many attempts. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            if len(self._hits) > 10_000:
                self._forget_idle(now, window_seconds)

    def _forget_idle(self, now: float, window_seconds: int) -> None:
        idle = [k for k, h in self._hits.items() if not h or h[-1] <= now - window_seconds]
        for key in idle:
            del self._hits[key]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def limit_attempts(request: Request, action: str, account: str | None) -> None:
    """5 per minute per IP, and 5 per minute per account when one is known."""
    limiter: RateLimiter = request.app.state.limiter
    limiter.hit(f"{action}:ip:{client_ip(request)}", LIMIT_PER_MINUTE, 60)
    if account is not None:
        limiter.hit(f"{action}:account:{account}", LIMIT_PER_MINUTE, 60)


def limit_custom(request: Request, key: str, limit: int, window_seconds: int) -> None:
    limiter: RateLimiter = request.app.state.limiter
    limiter.hit(key, limit, window_seconds)
