"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    env: str = "dev"  # dev | test | prod

    database_url: str = "postgresql+asyncpg://recruit:recruit@localhost:15432/recruit"
    redis_url: str = "redis://localhost:16379/0"

    # RS256 keypair as PEM. Empty in dev/test -> an ephemeral pair is generated
    # at first use (with a warning). Required when env == "prod".
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000  # 30 days

    email_provider: str = "console"  # console | resend
    resend_api_key: str = ""
    email_from: str = "Recruit-ME <noreply@example.com>"

    frontend_base_url: str = "http://localhost:3000"

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
