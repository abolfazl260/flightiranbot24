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
    telegram_admin_id: int = Field(
        default=106056586,
        validation_alias=AliasChoices("TELEGRAM_ADMIN_ID", "ADMIN_ID"),
    )
    database_url: str = "sqlite+aiosqlite:///./flightiran.db"
    log_level: str = "INFO"
    flight_tracking_enabled: bool = True
    flight_provider_url: str = "https://www.flightradar24.com/v1/search/web/find"
    flight_provider_details_url: str = "https://data-live.flightradar24.com/clickhandler/"
    currency_provider_url: str | None = None
    currency_proxy_url: str | None = None
    ticket_provider_url: str = "https://mz724.ir/"
    ticket_support_username: str = "@vlansupport"
    app_env: str = "development"
    web_app_enabled: bool = False
    web_app_url: str | None = None

    def validate_for_production(self) -> None:
        if (
            self.app_env.lower() == "production"
            and len(self.telegram_bot_token.get_secret_value()) < 20
        ):
            raise ValueError("TELEGRAM_BOT_TOKEN is too short for production")
        if self.web_app_enabled and not self.web_app_url:
            raise ValueError("WEB_APP_URL is required when WEB_APP_ENABLED=true")


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
