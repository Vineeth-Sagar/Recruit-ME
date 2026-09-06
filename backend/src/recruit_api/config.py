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

    # Object storage (MinIO locally, S3 in prod)
    s3_endpoint: str = "http://localhost:19000"
    s3_bucket: str = "recruit"
    s3_access_key: str = "recruit"
    s3_secret_key: str = "recruit-secret"
    s3_region: str = "us-east-1"

    # LLM (résumé parse; job matching lands in Phase 4.4)
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"

    # Site-credential encryption. Dev falls back to an all-zero key.
    credential_master_key: str = ""  # base64, 32 bytes -> version 1
    credential_master_keys: str = ""  # "1:<b64>,2:<b64>" for rotation
    credential_key_version: int = 1

    # Upload limits
    max_resume_bytes: int = 10 * 1024 * 1024

    frontend_base_url: str = "http://localhost:3000"

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
