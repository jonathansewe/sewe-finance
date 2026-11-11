"""FastAPI application factory.

`create_app()` builds the app: error handlers, the Origin check, CORS, then
every router under /api/v1. A factory (instead of a module-level app only)
lets tests build a fresh app (with fresh rate-limit counters) per test.
Run locally with:
    uv run uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_error_handlers
from app.routers import auth, health, sessions, two_factor
from app.security.rate_limit import RateLimiter

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SEWE Finance API", version="0.2.0")
    install_error_handlers(app)
    app.state.limiter = RateLimiter()
    # CORS decides which web pages may READ our responses. It is not access
    # control: the Origin check (security/origin.py) decides what we ACCEPT.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,  # exact origins, never "*"
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    for router in (health.router, auth.router, two_factor.router, sessions.router):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
