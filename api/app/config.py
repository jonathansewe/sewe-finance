"""Settings loaded from environment variables (and an optional .env file).

Every secret and every value that differs between laptop and production
lives here, so no other module reads os.environ directly. Pydantic checks
the types at startup, so a typo in an env var fails loudly, not later.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    # psycopg 3 driver; matches docker-compose.yml's default credentials.
    database_url: str = "postgresql+psycopg://sewe:sewe@localhost:5432/sewe"
    # Comma-separated list; the Expo web dev server runs on port 8081.
    allowed_origins: str = "http://localhost:8081"

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file is read once; tests clear the cache to override.
    return Settings()
