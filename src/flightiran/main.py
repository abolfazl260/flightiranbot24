"""Application entry point for the new Flight Iran Bot 24."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, ApplicationBuilder

from flightiran.config import ConfigurationError, Settings, load_settings
from flightiran.db import create_database, initialize_database
from flightiran.db.engine import Database
from flightiran.db.models import JobRun
from flightiran.db.repositories import (
    SQLiteAuditRepository,
    SQLiteMz724PriceHistoryRepository,
    SQLiteUserRepository,
)
from flightiran.infrastructure.http import ProviderHttpClient, ProviderHttpConfig
from flightiran.interfaces.telegram import TelegramDependencies, register_handlers
from flightiran.modules.admin.reports import BotReportRepository
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.currency.provider import HttpCurrencyProvider
from flightiran.modules.currency.service import CurrencyService
from flightiran.modules.flight_tracking.provider import HttpFlightProvider
from flightiran.modules.flight_tracking.service import FlightService
from flightiran.modules.tickets.mz724 import Mz724TicketProvider
from flightiran.modules.tickets.service import CheapTicketService
from flightiran.modules.useful_content import default_catalog
from flightiran.modules.visa.sync import VisaSyncService

LOGGER: Final = logging.getLogger("flightiran")


def configure_logging(level: str) -> None:
    """Configure a small, useful startup log for local and service execution."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_application(
    settings: Settings,
    cheap_ticket_service: CheapTicketService | None = None,
    *,
    report_database: Database | None = None,
    visa_sync_service: VisaSyncService | None = None,
) -> Application:
    """Build the Telegram application without starting network polling."""

    builder = ApplicationBuilder().token(settings.telegram_bot_token.get_secret_value())
    if cheap_ticket_service is not None or visa_sync_service is not None:

        async def post_init(application: Application) -> None:
            scheduler = AsyncIOScheduler(timezone="UTC")

            async def store_job_status(status: str) -> None:
                if report_database is None:
                    return
                async with report_database.session() as session:
                    session.add(
                        JobRun(
                            job_name="mz724-hourly-price-history",
                            status=status,
                            finished_at=datetime.now(timezone.utc),
                        )
                    )

            async def capture_prices() -> None:
                try:
                    count = await cheap_ticket_service.capture_price_snapshot()
                    await store_job_status("success")
                    LOGGER.info("mz724 hourly snapshot stored routes=%s", count)
                except Exception as exc:
                    LOGGER.exception("mz724 hourly snapshot failed")
                    try:
                        await store_job_status("failed")
                    except Exception:
                        LOGGER.exception("failed_to_store_job_run")
                    try:
                        await application.bot.send_message(
                            chat_id=settings.telegram_admin_id,
                            text=(
                                "FlightIranBot24 scheduled price capture failed\n"
                                f"Type: {type(exc).__name__}\n"
                                f"Message: {exc}"
                            ),
                        )
                    except Exception:
                        LOGGER.exception("failed_to_notify_admin_about_price_capture")

            if cheap_ticket_service is not None:
                scheduler.add_job(
                    capture_prices,
                    "interval",
                    minutes=settings.ticket_history_interval_minutes,
                    next_run_time=datetime.now(timezone.utc),
                    max_instances=1,
                    coalesce=True,
                    id="mz724-hourly-price-history",
                    replace_existing=True,
                )

            if visa_sync_service is not None and settings.visa_sync_enabled:
                async def sync_visas() -> None:
                    try:
                        result = await visa_sync_service.sync()
                        if result.status == "updated":
                            await application.bot.send_message(
                                chat_id=settings.telegram_admin_id,
                                text=result.render(manual=False),
                                disable_web_page_preview=True,
                            )
                        LOGGER.info(
                            "visa_sync status=%s downloads=%s changes=%s",
                            result.status, result.downloaded, len(result.changed),
                        )
                    except Exception as exc:
                        LOGGER.exception("scheduled_visa_sync_failed")
                        try:
                            await application.bot.send_message(
                                chat_id=settings.telegram_admin_id,
                                text=(
                                    "خطا در همگام‌سازی خودکار ویزا؛ آخرین داده سالم حفظ شد.\\n"
                                    f"{type(exc).__name__}: {str(exc)[:250]}\\n"
                                    "منبع: https://travelrequirements.info/data/index.json"
                                ).replace("\\\\n", "\\n"),
                                disable_web_page_preview=True,
                            )
                        except Exception:
                            LOGGER.exception("failed_to_notify_admin_about_visa_sync")
                scheduler.add_job(
                    sync_visas,
                    "interval",
                    hours=settings.visa_sync_interval_hours,
                    next_run_time=datetime.now(timezone.utc),
                    max_instances=1,
                    coalesce=True,
                    id="travelrequirements-visa-sync",
                    replace_existing=True,
                )
            scheduler.start()
            application.bot_data["price_history_scheduler"] = scheduler

        async def post_shutdown(application: Application) -> None:
            scheduler = application.bot_data.get("price_history_scheduler")
            if isinstance(scheduler, AsyncIOScheduler) and scheduler.running:
                scheduler.shutdown(wait=False)

        builder = builder.post_init(post_init).post_shutdown(post_shutdown)
    return builder.build()


def run() -> None:
    """Load configuration, build the application and start polling."""

    settings = load_settings()
    configure_logging(settings.log_level)
    database = asyncio.run(_initialize_database(settings.database_url))
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
        Mz724TicketProvider(ticket_http, url=settings.ticket_provider_url),
        SQLiteMz724PriceHistoryRepository(database),
        retention_days=settings.ticket_history_retention_days,
    )
    visa_sync_service = VisaSyncService(database) if settings.visa_sync_enabled else None
    application = create_application(
        settings,
        cheap_ticket_service,
        report_database=database,
        visa_sync_service=visa_sync_service,
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
            admin_reports=BotReportRepository(database),
            visa_sync_service=visa_sync_service,
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
