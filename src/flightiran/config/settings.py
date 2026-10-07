"""Environment-backed application settings."""

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is unavailable."""


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: SecretStr = Field(
        validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "BOT_TOKEN")
    )
    database_url: str = "sqlite+aiosqlite:///./flightiran.db"
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load settings once and expose a safe, user-facing configuration error."""

    try:
        return Settings()
    except ValidationError as exc:
        if any(error.get("type") == "missing" for error in exc.errors()):
            raise ConfigurationError(
                "Missing required configuration: TELEGRAM_BOT_TOKEN. "
                "Set it in the environment before starting the bot."
            ) from None
        raise ConfigurationError("Invalid application configuration.") from None
