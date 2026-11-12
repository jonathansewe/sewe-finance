"""Origin check on every state-changing request (D-16, SPEC 6.1).

Every *.jonathansewe.com host is the "same site" as the API, so
SameSite=Strict alone wouldn't stop a page on the resume site (or a buggy
future project) from making the browser POST here with our cookie. The
Origin header names the exact page that started a request, and page
scripts can't forge it. So, for POST/PATCH/PUT/DELETE:
  - Origin present → it must exactly equal an ALLOWED_ORIGINS entry;
  - Origin missing → allowed only when the request carries no cookies.
    That's the native app: it has no ambient credentials to abuse, and the
    endpoint itself still demands a Bearer token or a body refresh token.
GET/HEAD/OPTIONS are not checked: they never change anything.
"""

import json
import logging

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.errors import error_body

log = logging.getLogger("sewe.security")
_UNSAFE = {"POST", "PATCH", "PUT", "DELETE"}


class OriginCheckMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in _UNSAFE:
            headers = Headers(scope=scope)
            origin = headers.get("origin")
            if origin is not None:
                allowed = origin in self.allowed  # exact match; "null" never matches
            else:
                allowed = "cookie" not in headers
            if not allowed:
                log.info("origin.rejected")  # event only; no header values
                await _reject(send)
                return
        await self.app(scope, receive, send)


async def _reject(send: Send) -> None:
    body = json.dumps(
        error_body("origin_not_allowed", "Requests from this origin are not allowed")
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
