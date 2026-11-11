"""Production refuses to start with development defaults (D-36 guard and friends)."""

import pytest
from pydantic import ValidationError

from app.config import Settings

SAFE_PROD = {
    "app_env": "prod",
    "jwt_secret": "x" * 48,
    "data_encryption_key": "q83vEjRWeJq83vEjRWeJq83vEjRWeJq83vEjRWeJq80=",
    "forwarded_allow_ips": "10.0.0.0/8",
    "email_provider": "resend",
    "resend_api_key": "re_test_placeholder",
    "cookie_secure": True,
}


def test_safe_production_settings_load() -> None:
    assert Settings(**SAFE_PROD).app_env == "prod"  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["127.0.0.1", "", "  "])
def test_prod_refuses_default_forwarded_allow_ips(value: str) -> None:
    with pytest.raises(ValidationError, match="FORWARDED_ALLOW_IPS"):
        Settings(**{**SAFE_PROD, "forwarded_allow_ips": value})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "named"),
    [
        ("jwt_secret", "short", "JWT_SECRET"),
        ("data_encryption_key", Settings().data_encryption_key, "DATA_ENCRYPTION_KEY"),
        ("email_provider", "console", "EMAIL_PROVIDER"),
        ("cookie_secure", False, "COOKIE_SECURE"),
    ],
)
def test_prod_refuses_other_dev_defaults(field: str, value: object, named: str) -> None:
    with pytest.raises(ValidationError, match=named):
        Settings(**{**SAFE_PROD, field: value})  # type: ignore[arg-type]


def test_local_accepts_dev_defaults() -> None:
    assert Settings(app_env="local").forwarded_allow_ips == "127.0.0.1"
