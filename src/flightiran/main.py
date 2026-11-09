"""Application entry point for the new Flight Iran Bot 24."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import BotCommand, Update
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
from flightiran.interfaces.bale import BaleBot
from flightiran.interfaces.telegram import TelegramDependencies, register_handlers
from flightiran.interfaces.telegram.keyboards import telegram_web_app_url
from flightiran.interfaces.telegram.price_notifications import render_ticket_alert
from flightiran.interfaces.telegram.visa_watches import deliver_watch_notifications
from flightiran.modules.admin.daily_active import (
    ActiveUsersReportRepository,
    render_active_users_report,
)
from flightiran.modules.admin.reports import BotReportRepository
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.experiences.persistent import SQLiteExperienceService
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.mz724 import Mz724TicketProvider
from flightiran.modules.tickets.service import CheapTicketService
from flightiran.modules.travel_checklist import SQLiteTravelChecklistService
from flightiran.modules.useful_content import default_catalog
from flightiran.modules.visa.catalog import VisaCatalogService
from flightiran.modules.visa.sync import VisaSyncService
from flightiran.modules.visa.watch import VisaWatchService

LOGGER: Final = logging.getLogger("flightiran")


def configure_logging(level: str) -> None:
    """Configure a small, useful startup log for local and service execution."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


# Keep Telegram command menus in sync across deployments and languages.
BOT_COMMAND_DESCRIPTIONS = {
    "fa": {
        "start": "نمایش منوی اصلی",
        "help": "راهنمای استفاده از ربات",
        "language": "تغییر زبان",
        "alerts": "زنگوله قیمت بلیط",
        "fares": "کارت تعاملی قیمت بلیت",
        "chart": "نمودار قیمت مسیرهای پرواز",
        "checklist": "چک‌لیست سفر من",
        "airports": "راهنمای تعاملی فرودگاه‌ها",
        "visa": "اطلاعات ویزا",
        "visa_watch": "هشدار تغییرات ویزا",
        "visa_list": "کشورها بر اساس پاسپورت",
        "cancel": "لغو جست‌وجوی ویزا",
    },
    "en": {
        "start": "Open main menu",
        "help": "Help and commands",
        "language": "Change language",
        "alerts": "Ticket price alerts",
        "fares": "Interactive fare widget",
        "chart": "Route price history chart",
        "checklist": "My travel checklist",
        "airports": "Interactive airport guides",
        "visa": "Visa requirements",
        "visa_watch": "Visa change alerts",
        "visa_list": "Countries by passport",
        "cancel": "Cancel visa search",
    },
    "ar": {
        "start": "عرض القائمة الرئيسية",
        "help": "دليل الاستخدام",
        "language": "تغيير اللغة",
        "alerts": "تنبيهات أسعار التذاكر",
        "fares": "بطاقة أسعار الرحلات التفاعلية",
        "chart": "مخطط أسعار رحلات الطيران",
        "checklist": "قائمة الاستعداد للسفر",
        "airports": "دليل المطارات التفاعلي",
        "visa": "متطلبات التأشيرة",
        "visa_watch": "تنبيهات تغييرات التأشيرات",
        "visa_list": "الدول حسب جواز السفر",
        "cancel": "إلغاء البحث عن التأشيرة",
    },
}


async def _sync_telegram_commands(application: Application) -> None:
    """Replace legacy Telegram command menus, including localized menus."""

    for language, descriptions in BOT_COMMAND_DESCRIPTIONS.items():
        commands = [
            BotCommand(command, description)
            for command, description in descriptions.items()
        ]
        await application.bot.set_my_commands(commands, language_code=language)
        if language == "en":
            await application.bot.set_my_commands(commands)


def create_application(
    settings: Settings,
    cheap_ticket_service: CheapTicketService | None = None,
    *,
    report_database: Database | None = None,
    visa_sync_service: VisaSyncService | None = None,
    price_alert_service: PriceAlertService | None = None,
    visa_watch_service: VisaWatchService | None = None,
    platform: str = "telegram",
) -> Application:
    """Build a Telegram or Bale application with the same business handlers."""

    if platform == "bale":
        if settings.bale_bot_token is None or not settings.bale_bot_token.get_secret_value():
            raise ConfigurationError("BALE_BOT_TOKEN must be set to run the Bale bot")
        builder = ApplicationBuilder().bot(
            BaleBot(token=settings.bale_bot_token.get_secret_value())
        )
    elif platform == "telegram":
        builder = ApplicationBuilder().token(settings.telegram_bot_token.get_secret_value())
    else:
        raise ValueError("Unsupported messaging platform")

    admin_destination = (
        settings.bale_admin_id if platform == "bale" else settings.telegram_admin_id
    )
    if (
        cheap_ticket_service is not None or visa_sync_service is not None
        or visa_watch_service is not None
        or (report_database is not None and settings.active_users_report_enabled)
    ):

        async def post_init(application: Application) -> None:
            if platform == "telegram":
                await _sync_telegram_commands(application)
            # Bale does not document setMyCommands; avoid calling unsupported API.
            scheduler = AsyncIOScheduler(timezone="UTC")

            async def send_admin_message(**kwargs) -> None:
                if admin_destination is not None:
                    await application.bot.send_message(
                        chat_id=admin_destination, **kwargs
                    )

            async def store_job_status(
                status: str, job_name: str = "mz724-hourly-price-history"
            ) -> None:
                if report_database is None:
                    return
                async with report_database.session() as session:
                    session.add(
                        JobRun(
                            job_name=job_name,
                            status=status,
                            finished_at=datetime.now(timezone.utc),
                        )
                    )

            async def notify_price_alerts(samples: list[tuple[str, str, int]]) -> None:
                if price_alert_service is None or not samples:
                    return

                async def send_alert(telegram_id, origin, destination, alert, snapshot):
                    language = await SQLiteUserRepository(
                        price_alert_service.database
                    ).get_language(alert.user_id)
                    body = render_ticket_alert(
                        origin, destination, alert, snapshot, language,
                    )
                    try:
                        await application.bot.send_message(
                            chat_id=telegram_id, text=body, parse_mode="HTML"
                        )
                    except Exception:
                        LOGGER.exception(
                            "price_alert_telegram_delivery_failed alert_id=%s", alert.id
                        )
                        raise

                delivered = await price_alert_service.process_feed(samples, send_alert)
                if delivered:
                    LOGGER.info("mz724 alerts delivered count=%s", delivered)

            async def capture_prices() -> None:
                try:
                    count = await cheap_ticket_service.capture_price_snapshot(
                        on_samples=notify_price_alerts if price_alert_service else None
                    )
                    await store_job_status("success")
                    LOGGER.info("mz724 hourly snapshot stored routes=%s", count)
                except Exception as exc:
                    LOGGER.exception("mz724 hourly snapshot failed")
                    try:
                        await store_job_status("failed")
                    except Exception:
                        LOGGER.exception("failed_to_store_job_run")
                    try:
                        await send_admin_message(
                            
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
                            await send_admin_message(
                                
                                text=result.render(manual=False, html=True),
                                parse_mode="HTML",
                                disable_web_page_preview=True,
                            )
                        LOGGER.info(
                            "visa_sync status=%s downloads=%s changes=%s",
                            result.status, result.downloaded, len(result.changed),
                        )
                    except Exception as exc:
                        LOGGER.exception("scheduled_visa_sync_failed")
                        try:
                            await send_admin_message(
                                
                                text=(
                                    "خطا در همگام‌سازی خودکار ویزا؛ آخرین داده سالم حفظ شد.\n"
                                    f"{type(exc).__name__}: {str(exc)[:250]}\n"
                                    "منبع: https://travelrequirements.info/data/index.json"
                                ),
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
            if visa_watch_service is not None:
                async def send_pending_visa_alerts() -> None:
                    try:
                        delivered = await deliver_watch_notifications(
                            application.bot, visa_watch_service,
                            SQLiteUserRepository(visa_watch_service.database),
                        )
                        if delivered:
                            LOGGER.info("visa_change_notifications_sent count=%s", delivered)
                    except Exception:
                        LOGGER.exception("visa_change_notification_dispatch_failed")

                scheduler.add_job(
                    send_pending_visa_alerts,
                    "interval",
                    minutes=15,
                    next_run_time=datetime.now(timezone.utc),
                    max_instances=1,
                    coalesce=True,
                    id="visa-change-notification-outbox",
                    replace_existing=True,
                )
            if report_database is not None and settings.active_users_report_enabled:
                async def send_daily_users_report() -> None:
                    try:
                        now = datetime.now(timezone.utc)
                        users = await ActiveUsersReportRepository(report_database).collect(now)
                        pages = render_active_users_report(
                            users, now=now,
                            report_timezone=settings.active_users_report_timezone,
                        )
                        for page in pages:
                            await send_admin_message(
                                
                                text=page, parse_mode="HTML",
                                disable_web_page_preview=True,
                            )
                        await store_job_status("success", "daily-active-users-report")
                        LOGGER.info(
                            "daily active users delivered users=%s messages=%s",
                            len(users), len(pages),
                        )
                    except Exception:
                        LOGGER.exception("daily_active_users_report_failed")
                        try:
                            await store_job_status("failed", "daily-active-users-report")
                        except Exception:
                            LOGGER.exception("failed_to_store_daily_active_users_job_status")

                hour, minute = map(int, settings.active_users_report_time.split(":"))
                scheduler.add_job(
                    send_daily_users_report,
                    "cron",
                    hour=hour, minute=minute,
                    timezone=ZoneInfo(settings.active_users_report_timezone),
                    max_instances=1, coalesce=True, misfire_grace_time=3600,
                    id="daily-active-users-report", replace_existing=True,
                )

            scheduler.start()
            application.bot_data["price_history_scheduler"] = scheduler

        async def post_shutdown(application: Application) -> None:
            scheduler = application.bot_data.get("price_history_scheduler")
            if isinstance(scheduler, AsyncIOScheduler) and scheduler.running:
                scheduler.shutdown(wait=False)

        builder = builder.post_init(post_init).post_shutdown(post_shutdown)
    elif platform == "telegram":
        builder = builder.post_init(_sync_telegram_commands)
    return builder.build()


def run(*, platform: str = "telegram") -> None:
    """Load configuration and start the selected messaging process."""

    settings = load_settings()
    if platform == "bale" and (
        settings.bale_bot_token is None or not settings.bale_bot_token.get_secret_value()
    ):
        raise ConfigurationError("Missing required configuration: BALE_BOT_TOKEN")
    configure_logging(settings.log_level)
    database_url = (
        settings.bale_database_url if platform == "bale" else settings.database_url
    )
    database = asyncio.run(_initialize_database(database_url))
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
    price_alert_service = PriceAlertService(database) if settings.price_alerts_enabled else None
    visa_watch_service = VisaWatchService(database) if settings.visa_watch_enabled else None
    application = create_application(
        settings,
        cheap_ticket_service,
        report_database=database,
        visa_sync_service=visa_sync_service,
        price_alert_service=price_alert_service,
        visa_watch_service=visa_watch_service,
        platform=platform,
    )
    # Bad Web App URLs must never take down /start: Telegram allows HTTPS only.
    web_app_url = (
        telegram_web_app_url(settings.web_app_url)
        if platform == "telegram" and settings.web_app_enabled else None
    )
    if platform == "telegram" and settings.web_app_enabled and web_app_url is None:
        LOGGER.warning(
            "Telegram Web App button skipped: WEB_APP_URL must be a valid HTTPS URL; "
            "bot menus and public price API remain available"
        )
    register_handlers(
        application,
        TelegramDependencies(
            users=SQLiteUserRepository(database),
            audit=SQLiteAuditRepository(database),
            web_app_url=web_app_url,
            airport_catalog=AirportCatalog.from_json(
                Path(__file__).parent / "modules" / "airport" / "data" / "airports.json"
            ),
            cheap_ticket_service=cheap_ticket_service,
            checklist_service=(
                SQLiteTravelChecklistService(database) if platform == "telegram" else None
            ),
            price_alert_service=price_alert_service,
            ticket_support_username=settings.ticket_support_username,
            admin_chat_id=(
                settings.bale_admin_id if platform == "bale" else settings.telegram_admin_id
            ),
            admin_reports=BotReportRepository(database),
            visa_sync_service=visa_sync_service,
            visa_watch_service=visa_watch_service,
            visa_catalog=VisaCatalogService(
                database, stale_after_hours=settings.visa_stale_after_hours
            ),
            useful_catalog=default_catalog(),
            experience_service=(
                SQLiteExperienceService(database) if platform == "telegram" else None
            ),
        ),
    )
    LOGGER.info("Flight Iran Bot 24 started platform=%s", platform)
    if platform == "telegram":
        # Include new updates even before python-telegram-bot exposes their constants.
        allowed_updates = list(dict.fromkeys((*Update.ALL_TYPES, "widget_query")))
        application.run_polling(allowed_updates=allowed_updates)
    else:
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


def bale_main() -> None:
    """Separate entry point so both services can poll concurrently."""

    try:
        run(platform="bale")
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(message)s")
        logging.getLogger("flightiran").error("Startup configuration error: %s", exc)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
