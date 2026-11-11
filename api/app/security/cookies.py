"""The refresh-token cookie: the only cookie the API ever sets (SPEC 6.1).

HttpOnly (page scripts can't read it), Secure (HTTPS only), SameSite=Strict
(other sites can't make the browser send it), Path=/api/v1/auth/refresh
(sent to that one endpoint only), and **never** a Domain attribute, so it
stays host-only on the API's own hostname (D-17). Setting cookies anywhere
else is a bug; tests/test_cookies.py checks every Set-Cookie header.
"""

from fastapi import Request, Response

from app.config import get_settings

REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/v1/auth/refresh"


def is_browser(request: Request) -> bool:
    """Browsers always send Origin on POST; the native app never does (D-16).

    Browsers get the refresh token as a cookie; native clients get it in
    the JSON body and keep it in expo-secure-store.
    """
    return "origin" in request.headers


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_days * 24 * 3600,
        path=REFRESH_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
        # domain deliberately not passed: host-only cookie (D-17)
    )


def clear_refresh_cookie(response: Response) -> None:
    # A response may clear a cookie for any path on its own host, so logout
    # can clear it even though the browser never sent it to /logout (D-18).
    response.set_cookie(
        REFRESH_COOKIE,
        "",
        max_age=0,
        path=REFRESH_PATH,
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="strict",
    )
