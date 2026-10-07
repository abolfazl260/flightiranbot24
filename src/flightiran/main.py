"""Application entry point for the new Flight Iran Bot 24."""

import logging
from typing import Final

from telegram.ext import Application, ApplicationBuilder

from flightiran.config import ConfigurationError, Settings, load_settings

LOGGER: Final = logging.getLogger("flightiran")


def configure_logging(level: str) -> None:
    """Configure a small, useful startup log for local and service execution."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_application(settings: Settings) -> Application:
    """Build the Telegram application without starting network polling."""

    return ApplicationBuilder().token(settings.telegram_bot_token.get_secret_value()).build()


def run() -> None:
    """Load configuration, build the application and start polling."""

    settings = load_settings()
    configure_logging(settings.log_level)
    application = create_application(settings)
    LOGGER.info("Flight Iran Bot 24 started")
    application.run_polling()


def main() -> None:
    """CLI wrapper with safe configuration failure output."""

    try:
        run()
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(message)s")
        logging.getLogger("flightiran").error("Startup configuration error: %s", exc)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()

