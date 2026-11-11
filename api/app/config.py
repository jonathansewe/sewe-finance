"""Settings loaded from environment variables (and an optional .env file).

Every secret and every value that differs between laptop and production
lives here, so no other module reads os.environ directly. Pydantic checks
the types at startup, so a typo in an env var fails loudly, not later.
In production, `_refuse_unsafe_production_values` stops the app from
starting with a development default left in place.
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Development-only defaults. Production must override them (checked below).
DEV_JWT_SECRET = "dev-only-jwt-secret-do-not-use-in-production-0000"  # noqa: S105
# 32 zero bytes, base64. Fine for a laptop, refused in production.
DEV_DATA_ENCRYPTION_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "prod"] = "local"
    # psycopg 3 driver; matches docker-compose.yml's default credentials.
    database_url: str = "postgresql+psycopg://sewe:sewe@localhost:5432/sewe"
    # Comma-separated list; the Expo web dev server runs on port 8081.
    allowed_origins: str = "http://localhost:8081"

    # --- Auth (SPEC 6.1, 6.2) ---
    jwt_secret: str = DEV_JWT_SECRET
    data_encryption_key: str = DEV_DATA_ENCRYPTION_KEY
    access_token_minutes: int = 15
    mfa_token_minutes: int = 5
    refresh_token_days: int = 30
    refresh_grace_seconds: int = 20  # D-34
    cookie_secure: bool = True

    # --- Email (D-25) ---
    email_provider: Literal["console", "resend"] = "console"
    resend_api_key: str = ""
    email_from: str = "SEWE Finance <finance@jonathansewe.com>"  # Q16

    # --- Passkeys (SPEC 6.1) ---
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "SEWE Finance"
    webauthn_origin: str = "http://localhost:8081"

    # The same variable uvicorn reads for --forwarded-allow-ips (D-36).
    # Only these peers may set the client IP through X-Forwarded-For.
    forwarded_allow_ips: str = "127.0.0.1"

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _refuse_unsafe_production_values(self) -> Self:
        if self.app_env != "prod":
            return self
        problems: list[str] = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be a random value of at least 32 characters")
        if self.data_encryption_key == DEV_DATA_ENCRYPTION_KEY:
            problems.append("DATA_ENCRYPTION_KEY must not be the development key")
        proxies = {ip.strip() for ip in self.forwarded_allow_ips.split(",") if ip.strip()}
        if proxies <= {"127.0.0.1", "::1"}:
            # Behind Render's proxy every request would come from the proxy's
            # IP, so one shared per-IP rate limit would lock everyone out.
            problems.append("FORWARDED_ALLOW_IPS must name the hosting proxy, not 127.0.0.1")
        elif "*" in proxies:
            # "*" trusts every hop, so uvicorn would take the left-most
            # X-Forwarded-For entry: the one the client writes itself.
            problems.append("FORWARDED_ALLOW_IPS must not be *: clients could spoof their IP")
        if self.email_provider != "resend" or not self.resend_api_key:
            problems.append("EMAIL_PROVIDER must be resend, with RESEND_API_KEY set")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true")
        if problems:
            raise ValueError("Unsafe production settings: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file is read once; tests clear the cache to override.
    return Settings()
