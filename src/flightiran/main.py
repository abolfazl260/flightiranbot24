"""Application entry point for the new Flight Iran Bot 24."""

import asyncio
import logging
from pathlib import Path
from typing import Final

from telegram.ext import Application, ApplicationBuilder

from flightiran.config import ConfigurationError, Settings, load_settings
from flightiran.db import create_database, initialize_database
from flightiran.db.engine import Database
from flightiran.db.repositories import SQLiteAuditRepository, SQLiteUserRepository
from flightiran.infrastructure.http import ProviderHttpClient, ProviderHttpConfig
from flightiran.interfaces.telegram import TelegramDependencies, register_handlers
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.currency.provider import HttpCurrencyProvider
from flightiran.modules.currency.service import CurrencyService
from flightiran.modules.flight_tracking.provider import HttpFlightProvider
from flightiran.modules.flight_tracking.service import FlightService
from flightiran.modules.tickets.mz724 import Mz724TicketProvider
from flightiran.modules.tickets.service import CheapTicketService
from flightiran.modules.useful_content import default_catalog

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
    database = asyncio.run(_initialize_database(settings.database_url))
    application = create_application(settings)
    currency_service = None
    if settings.currency_provider_url:
        currency_service = CurrencyService(
            HttpCurrencyProvider(
                ProviderHttpClient(ProviderHttpConfig(cache_ttl_seconds=30)),
                settings.currency_provider_url,
            )
        )
    flight_http_client = ProviderHttpClient(
        ProviderHttpConfig(
            cache_ttl_seconds=15,
            default_headers={"User-Agent": "FlightIranBot24/1.0"},
        )
    )
    flight_service = FlightService(
        HttpFlightProvider(
            flight_http_client,
            settings.flight_provider_url,
            details_endpoint=settings.flight_provider_details_url,
        ),
        enabled=settings.flight_tracking_enabled,
    )
    ticket_http = ProviderHttpClient(
        ProviderHttpConfig(
            timeout_seconds=12,
            max_retries=2,
            cache_ttl_seconds=60,
            default_headers={"Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8"},
        )
    )
    cheap_ticket_service = CheapTicketService(
        Mz724TicketProvider(ticket_http, url=settings.ticket_provider_url)
    )
    register_handlers(
        application,
        TelegramDependencies(
            users=SQLiteUserRepository(database),
            audit=SQLiteAuditRepository(database),
            web_app_url=settings.web_app_url if settings.web_app_enabled else None,
            airport_catalog=AirportCatalog.from_json(
                Path(__file__).parent / "modules" / "airport" / "data" / "airports.json"
            ),
            currency_service=currency_service,
            flight_service=flight_service,
            cheap_ticket_service=cheap_ticket_service,
            ticket_support_username=settings.ticket_support_username,
            admin_chat_id=settings.telegram_admin_id,
            useful_catalog=default_catalog(),
        ),
    )
    LOGGER.info("Flight Iran Bot 24 started")
    application.run_polling()


async def _initialize_database(database_url: str) -> Database:
    initialized = await initialize_database(database_url)
    await initialized.close()
    return create_database(database_url)


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
