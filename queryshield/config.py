"""Centralized settings — one place for env-var reads.

Pattern matches the rest of Brett's agentic-build projects: a singleton
``Settings`` instance loaded once at import, with conservative defaults so
local development works without a .env file.
"""
from __future__ import annotations

import functools
import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # AI
    anthropic_api_key: Optional[str] = None
    nl_to_sql_model: str = "claude-sonnet-4-6"

    # Internal control-plane DB
    database_url: str = "sqlite:///queryshield_local.db"

    # Vault
    vault_key: Optional[str] = None  # Fernet key (base64) — required in prod

    # Cache
    redis_url: Optional[str] = None

    # Billing
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_starter: Optional[str] = None
    stripe_price_pro: Optional[str] = None
    stripe_price_enterprise: Optional[str] = None

    # Notifications
    sendgrid_api_key: Optional[str] = None
    sendgrid_from: str = "alerts@queryshield.io"
    discord_webhook_url: Optional[str] = None

    # Runtime
    port: int = 8000
    env: str = "development"
    log_level: str = "INFO"
    max_rows_hard_limit: int = 5000
    public_base_url: str = "http://localhost:8000"

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Pydantic-settings honors the constructor kwargs taking precedence over env;
    # ENVIRONMENT is the more idiomatic name in deploy configs.
    return Settings(env=os.getenv("ENVIRONMENT", "development"))
