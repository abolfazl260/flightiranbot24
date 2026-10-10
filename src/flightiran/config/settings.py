"""Environment-backed application settings."""

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SUPPORT_USERNAME = "@advertio_support"


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
    ticket_provider_url: str = "https://mz724.ir/"
    ticket_support_username: str = Field(
        default=DEFAULT_SUPPORT_USERNAME,
        validation_alias=AliasChoices("SUPPORT_USERNAME", "TICKET_SUPPORT_USERNAME"),
    )
    ticket_history_interval_minutes: int = 60
    ticket_history_retention_days: int = 21
    price_alerts_enabled: bool = True
    app_env: str = "development"
    visa_sync_enabled: bool = True
    visa_sync_interval_hours: int = 6
    visa_stale_after_hours: int = 24
    visa_watch_enabled: bool = True
    active_users_report_enabled: bool = True
    active_users_report_time: str = "09:00"
    active_users_report_timezone: str = "Asia/Tehran"
    web_app_enabled: bool = False
    web_app_url: str | None = None

    @field_validator("active_users_report_time")
    @classmethod
    def check_daily_report_time(cls, value: str) -> str:
        try:
            hour, minute = map(int, value.split(":"))
        except (ValueError, TypeError) as exc:
            raise ValueError("ACTIVE_USERS_REPORT_TIME must be HH:MM") from exc
        if not 0 <= hour <= 23 or not 0 <= minute <= 59 or len(value) != 5:
            raise ValueError("ACTIVE_USERS_REPORT_TIME must be HH:MM (24-hour)")
        return value

    @field_validator("active_users_report_timezone")
    @classmethod
    def check_report_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("ACTIVE_USERS_REPORT_TIMEZONE must be an IANA zone") from exc
        return value

    @field_validator("ticket_support_username")
    @classmethod
    def normalize_legacy_support_username(cls, username: str) -> str:
        """Redirect obsolete support usernames to the current support account."""

        if username.strip().lower().lstrip("@") in {"vlansupport", "advertio_bot"}:
            return DEFAULT_SUPPORT_USERNAME
        return username

    def validate_for_production(self) -> None:
        if (
            self.app_env.lower() == "production"
            and len(self.telegram_bot_token.get_secret_value()) < 20
        ):
            raise ValueError("TELEGRAM_BOT_TOKEN is too short for production")
        if self.web_app_enabled and not self.web_app_url:
            raise ValueError("WEB_APP_URL is required when WEB_APP_ENABLED=true")
        if self.visa_sync_interval_hours < 1:
            raise ValueError("VISA_SYNC_INTERVAL_HOURS must be positive")
        if self.visa_stale_after_hours < 1:
            raise ValueError("VISA_STALE_AFTER_HOURS must be positive")
        if self.ticket_history_interval_minutes < 1:
            raise ValueError("TICKET_HISTORY_INTERVAL_MINUTES must be positive")
        if self.ticket_history_retention_days < 1:
            raise ValueError("TICKET_HISTORY_RETENTION_DAYS must be positive")


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
