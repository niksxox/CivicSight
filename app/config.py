"""
CivicSight AI Service
Application configuration.

All secrets and environment-specific configuration are loaded
from environment variables / .env.

Never hard-code API keys or other secrets in this file.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables take precedence over values from .env.
    """

    app_name: str = Field(
        default="CivicSight AI Service",
        description="Application name",
    )

    app_version: str = Field(
        default="0.1.0",
        description="Application version",
    )

    environment: str = Field(
        default="development",
        description="Current application environment",
    )

    groq_api_key: SecretStr = Field(
        ...,
        description="Groq API key",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return the cached application settings.

    Caching prevents repeatedly reading and validating configuration.
    """
    return Settings()


settings = get_settings()