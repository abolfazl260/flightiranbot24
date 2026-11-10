"""Telegram handlers kept free of provider and SQL details."""

import logging
import traceback
from dataclasses import dataclass
from types import SimpleNamespace

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from flightiran.config.settings import DEFAULT_SUPPORT_USERNAME
from flightiran.db.repositories import AuditRepository, UserRepository
from flightiran.infrastructure.http.errors import ProviderError
from flightiran.interfaces.telegram.rich_tickets import (
    find_price_drops,
    render_price_drop_fallback_chunks,
    render_rich_price_drop_report,
    render_rich_price_tables,
    render_ticket_footer,
    send_rich_price_table,
    send_rich_price_table_with_badge_fallback,
)
from flightiran.modules.admin.reports import BotReportRepository
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.experiences.persistent import SQLiteExperienceService
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.service import CheapTicketService
from flightiran.modules.travel_checklist import SQLiteTravelChecklistService
from flightiran.modules.useful_content import UsefulContentCatalog, default_catalog
from flightiran.modules.visa.catalog import VisaCatalogService
from flightiran.modules.visa.sync import VisaSyncService
from flightiran.modules.visa.watch import VisaWatchService

from .admin_report_rich import (
    render_admin_report_fallback,
    render_rich_admin_report,
    render_rich_user_activity_reports,
    render_user_activity_fallback,
)
from .airport_widget import AirportGuideStore, handle_airport_widget_query, send_airport_widget
from .checklist_widget import handle_checklist_query, send_checklist_widget
from .experiences import handle_experience_callback, review_id, show_experiences, start_target
from .help_widget import PrivateChatMessage, handle_help_widget_query, send_help_widget
from .keyboards import (
    back_menu,
    language_menu,
    main_menu,
    support_menu,
    ticket_origins_menu,
    ticket_result_menu,
)
from .localization import normalize_language, safe_text, text
from .new_user_alert import render_new_user_alert
from .price_alerts import (
    handle_alert_callback,
    handle_alert_text,
    menu_keyboard,
    send_rich_alerts,
    word,
)
from .renderers import render_help, render_language_prompt, render_main_menu
from .route_chart import handle_chart_callback, open_chart_picker
from .support import render_support_message
from .useful_content import (
    USEFUL_CATEGORY_IDS,
    render_useful_category,
    useful_category_menu,
    useful_menu,
)
from .useful_widget import handle_useful_widget_query, send_useful_widget
from .visa_flow import (
    handle_visa_callback,
    open_visa_menu,
    open_visa_route,
    parse_visa_start_payload,
    visa_command,
    visa_search_text,
)
from .visa_watches import deliver_watch_notifications, handle_watch_callback, show_watches
from .visa_watches import word as visa_watch_text
from .visa_widget import handle_visa_widget_query, send_visa_widget
from .widgets import send_fare_widget, widget_query_handler

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramDependencies:
    users: UserRepository
    audit: AuditRepository
    web_app_url: str | None = None
    airport_catalog: AirportCatalog | None = None
    useful_catalog: UsefulContentCatalog | None = None
    cheap_ticket_service: CheapTicketService | None = None
    checklist_service: SQLiteTravelChecklistService | None = None
    price_alert_service: PriceAlertService | None = None
    ticket_support_username: str = DEFAULT_SUPPORT_USERNAME
    admin_chat_id: int | None = 106056586
    admin_reports: BotReportRepository | None = None
    visa_sync_service: VisaSyncService | None = None
    visa_catalog: VisaCatalogService | None = None
    visa_watch_service: VisaWatchService | None = None
    experience_service: SQLiteExperienceService | None = None


def _airport_store(dependencies: TelegramDependencies) -> AirportGuideStore | None:
    """Use the identity catalog already wired into the existing application."""
    if dependencies.airport_catalog is None:
        return None
    return AirportGuideStore(dependencies.airport_catalog)


def _widget_menu_enabled(update: Update, context: object | None) -> bool:
    """Offer HTML widgets only for Telegram private chats, if context is present."""
    if context is None:
        return False
    bot = getattr(context, "bot", None)
    chat = getattr(update, "effective_chat", None)
    return (
        getattr(bot, "platform", "telegram") != "bale"
        and getattr(chat, "type", None) == "private"
    )


def _is_private_admin(update: Update, dependencies: TelegramDependencies) -> bool:
    """Require the configured admin's user ID and their private chat ID."""

    user = update.effective_user
    chat = getattr(update, "effective_chat", None)
    return bool(
        user is not None
        and chat is not None
        and user.id == dependencies.admin_chat_id
        and chat.id == dependencies.admin_chat_id
        and chat.type == "private"
    )


async def _notify_admin(
    context: ContextTypes.DEFAULT_TYPE,
    error: BaseException,
    update: object,
    dependencies: TelegramDependencies,
) -> None:
    """Send a compact runtime error report to the configured platform admin."""

    if dependencies.admin_chat_id is None:
        return

    user_id = None
    chat_id = None
    update_id = None
    if isinstance(update, Update):
        update_id = update.update_id
        if update.effective_user is not None:
            user_id = update.effective_user.id
        if update.effective_chat is not None:
            chat_id = update.effective_chat.id

    traceback_text = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    report = (
        "🚨 FlightIranBot24 runtime error\n"
        f"Type: {type(error).__name__}\n"
        f"Message: {error}\n"
        f"User ID: {user_id or '-'}\n"
        f"Chat ID: {chat_id or '-'}\n"
        f"Update ID: {update_id if update_id is not None else '-'}\n\n"
        "Traceback:\n"
        f"{traceback_text}"
    )
    if len(report) > 4000:
        report = report[:4000] + "\n...[truncated]"

    try:
        await context.bot.send_message(chat_id=dependencies.admin_chat_id, text=report)
    except Exception:
        LOGGER.exception("failed_to_notify_admin")


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
    dependencies: TelegramDependencies,
) -> None:
    """Log unhandled Telegram errors and forward them to the admin."""

    error = context.error
    if error is None:
        return
    LOGGER.error(
        "Unhandled Telegram error",
        exc_info=(type(error), error, error.__traceback__),
    )
    try:
        await dependencies.audit.record(
            "system.error",
            payload={"type": type(error).__name__},
        )
    except Exception:
        LOGGER.exception("failed_to_record_runtime_error")
    await _notify_admin(context, error, update, dependencies)


async def user_activity_handler(
    update: Update, _context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    """Observe every Telegram update, including callbacks and inline queries."""
    user = update.effective_user
    if user is None or user.is_bot:
        return
    try:
        await dependencies.users.mark_active(
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    except Exception:
        LOGGER.exception("telegram_user_activity_tracking_failed")


async def _user_language(update: Update, dependencies: TelegramDependencies) -> tuple[int, str]:
    user = update.effective_user
    if user is None:
        raise ValueError("Telegram update has no effective user")
    record = await dependencies.users.get_or_create(
        user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    language = await dependencies.users.get_language(record.id)
    return record.id, normalize_language(language)


async def _load_visa_passport(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, dependencies: TelegramDependencies
) -> None:
    """Restore a changed passport across bot restarts; first-time users default to IR."""
    if not context.user_data.get("visa_passport"):
        context.user_data["visa_passport"] = await dependencies.users.get_visa_passport(user_id)


async def _save_visa_passport(
    context: ContextTypes.DEFAULT_TYPE, user_id: int,
    dependencies: TelegramDependencies, previous: str
) -> None:
    selected = context.user_data.get("visa_passport")
    if selected and selected != previous:
        await dependencies.users.set_visa_passport(user_id, selected)


async def start_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    telegram_user = update.effective_user
    if telegram_user is None:
        return
    # An atomic INSERT guards against duplicate alerts from repeated/concurrent /start.
    registered, is_new = await dependencies.users.get_or_create_with_status(
        telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )
    language = normalize_language(await dependencies.users.get_language(registered.id))
    if context is not None:
        context.user_data.pop("price_alert_pending", None)
    await dependencies.audit.record("user.start", user_id=registered.id)
    # Telegram /start payloads from the mobile app are a fixed allowlist.
    # Unknown payloads use the ordinary menu and never run privileged actions.
    args = getattr(context, "args", None) or ()
    entrypoint = args[0] if args else ""
    visa_route = parse_visa_start_payload(entrypoint)
    if update.message:
        if start_target(entrypoint) is not None:
            await show_experiences(update.message, dependencies.experience_service,
                                   dependencies.web_app_url, target=start_target(entrypoint),
                                   review=review_id(entrypoint))
        elif entrypoint == "visa_widget":
            opened = False
            if _widget_menu_enabled(update, context):
                opened = await send_visa_widget(
                    update.message, context, dependencies.visa_catalog,
                    dependencies.visa_watch_service, dependencies.users, registered.id, language
                )
            if not opened:
                await _load_visa_passport(context, registered.id, dependencies)
                await open_visa_menu(
                    update, context, dependencies.visa_catalog, language, edit=False
                )
        elif entrypoint == "visa":
            await dependencies.audit.record("visa.opened", user_id=registered.id)
            await _load_visa_passport(context, registered.id, dependencies)
            await open_visa_menu(
                update, context, dependencies.visa_catalog, language, edit=False
            )
        elif visa_route is not None:
            await dependencies.audit.record("visa.opened", user_id=registered.id)
            await open_visa_route(
                update, context, dependencies.visa_catalog, language, *visa_route
            )
        elif entrypoint == "fares" and _widget_menu_enabled(update, context):
            # Telegram private-chat deep link: https://t.me/Flightiranbot?start=fares
            # Reuse the same widget, provider and fallback as the /fares command.
            await dependencies.audit.record("ticket.widget.opened", user_id=registered.id)
            await send_fare_widget(
                update.message, context.bot, dependencies.cheap_ticket_service
            )
        elif entrypoint == "chart" and _widget_menu_enabled(update, context):
            await dependencies.audit.record("ticket.chart.opened", user_id=registered.id)
            await open_chart_picker(
                update.message, context.bot,
                getattr(dependencies.cheap_ticket_service, "price_history", None),
                context.user_data,
            )
        elif entrypoint == "checklist" and _widget_menu_enabled(update, context):
            # Private deep link: https://t.me/Flightiranbot?start=checklist
            await dependencies.audit.record("checklist.opened", user_id=registered.id)
            await send_checklist_widget(
                update.message, context.bot, dependencies.checklist_service
            )
        elif entrypoint == "alerts":
            if dependencies.price_alert_service is None:
                await update.message.reply_text(
                    word(language, "unavailable"), reply_markup=back_menu(language)
                )
            else:
                await update.message.reply_text(
                    "🔔 <b>زنگوله قیمت بلیت</b>\n"
                    "برای مشاهده هشدارهای ذخیره‌شده یا ثبت هشدار جدید، گزینه زیر را بزنید.",
                    parse_mode="HTML",
                    reply_markup=menu_keyboard(language),
                )
        elif entrypoint == "help" and _widget_menu_enabled(update, context):
            await dependencies.audit.record("user.help", user_id=registered.id)
            await send_help_widget(
                update.message, context.bot, language, dependencies.ticket_support_username,
            )
        elif entrypoint == "airports" and _widget_menu_enabled(update, context):
            await dependencies.audit.record("airport.widget.opened", user_id=registered.id)
            await send_airport_widget(
                update.message, context.bot, _airport_store(dependencies),
                dependencies.web_app_url,
            )
        elif entrypoint == "useful":
            await useful_command_handler(update, context, dependencies)
        elif entrypoint == "useful_legacy":
            await useful_command_handler(update, context, dependencies, legacy=True)
        else:
            await update.message.reply_text(
                render_main_menu(language, telegram_user.first_name),
                parse_mode="HTML",
                reply_markup=main_menu(
                    language,
                    dependencies.web_app_url,
                    is_admin=_is_private_admin(update, dependencies),
                    widgets_enabled=_widget_menu_enabled(update, context),
                ),
            )
    if is_new:
        await dependencies.audit.record("user.registered", user_id=registered.id)
        if (context is not None and getattr(context, "bot", None) is not None
                and dependencies.admin_chat_id is not None):
            try:
                await context.bot.send_message(
                    chat_id=dependencies.admin_chat_id,
                    text=render_new_user_alert(
                        telegram_user, getattr(registered, "created_at", None)
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception:
                # A blocked/unreachable admin must not prevent users from using the bot.
                LOGGER.exception("new_user_admin_alert_failed telegram_id=%s", telegram_user.id)


async def help_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    user_id, language = await _user_language(update, dependencies)
    await dependencies.audit.record("user.help", user_id=user_id)
    if update.message:
        can_widget = _widget_menu_enabled(update, context)
        keyboard = main_menu(
            language, dependencies.web_app_url,
            is_admin=_is_private_admin(update, dependencies),
            widgets_enabled=can_widget,
        )
        if not can_widget:
            # Preserve the original text help for Bale, groups and tests
            # without a Telegram context.
            await update.message.reply_text(
                render_help(language, dependencies.ticket_support_username),
                parse_mode="HTML", reply_markup=keyboard,
            )
        else:
            await send_help_widget(
                update.message, context.bot, language, dependencies.ticket_support_username,
                fallback_markup=keyboard,
            )


async def language_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    _user_id, language = await _user_language(update, dependencies)
    if update.message:
        await update.message.reply_text(
            render_language_prompt(language), parse_mode="HTML", reply_markup=language_menu()
        )


async def callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    user_id, language = await _user_language(update, dependencies)
    data = query.data or ""
    if data.startswith("xp:"):
        await handle_experience_callback(query, dependencies.experience_service)
        return
    if data == "menu:experiences":
        await show_experiences(query.message, dependencies.experience_service,
                               dependencies.web_app_url)
        return
    if data == "menu:help_widget" and _widget_menu_enabled(update, context):
        await dependencies.audit.record("user.help", user_id=user_id)
        await send_help_widget(
            query.message, context.bot, language, dependencies.ticket_support_username,
        )
        return
    if data == "menu:airports" and _widget_menu_enabled(update, context):
        await dependencies.audit.record("airport.widget.opened", user_id=user_id)
        await send_airport_widget(
            query.message, context.bot, _airport_store(dependencies), dependencies.web_app_url
        )
        return
    if data == "menu:route_chart" or data.startswith("chart:"):
        history = getattr(dependencies.cheap_ticket_service, "price_history", None)
        if data == "menu:route_chart":
            await dependencies.audit.record("ticket.chart.opened", user_id=user_id)
            await open_chart_picker(query, context.bot, history, context.user_data)
        else:
            await handle_chart_callback(query, context, history)
        return
    if data == "menu:checklist":
        if getattr(context.bot, "platform", "telegram") == "bale":
            await query.message.reply_text("چک‌لیست تعاملی فقط در تلگرام فعال است.")
        else:
            await dependencies.audit.record("checklist.opened", user_id=user_id)
            await send_checklist_widget(
                query.message, context.bot, dependencies.checklist_service
            )
        return
    if data == "menu:fare_widget":
        if getattr(context.bot, "platform", "telegram") == "bale":
            await query.message.reply_text("ویجت HTML فعلاً فقط در تلگرام فعال است.")
        else:
            await send_fare_widget(query.message, context.bot, dependencies.cheap_ticket_service)
        return
    if (
        data == "menu:price_alerts"
        or data.startswith(("alerts:", "tickets:alert:"))
    ):
        if dependencies.price_alert_service is None:
            await query.edit_message_text(
                word(language, "unavailable"), reply_markup=back_menu(language)
            )
            return
        await handle_alert_callback(
            update, context, dependencies.price_alert_service,
            dependencies.cheap_ticket_service, user_id, language,
        )
        return
    if data.startswith("visa:watch:"):
        await _load_visa_passport(context, user_id, dependencies)
        await handle_watch_callback(
            update, context, dependencies.visa_watch_service, user_id, language
        )
        return
    if data == "menu:visa" and _widget_menu_enabled(update, context):
        if await send_visa_widget(query.message, context, dependencies.visa_catalog,
            dependencies.visa_watch_service, dependencies.users, user_id, language):
            return
    if data == "menu:visa":
        await dependencies.audit.record("visa.opened", user_id=user_id)
        await _load_visa_passport(context, user_id, dependencies)
        await open_visa_menu(update, context, dependencies.visa_catalog, language)
        return
    if data.startswith("visa:"):
        await _load_visa_passport(context, user_id, dependencies)
        previous = context.user_data["visa_passport"]
        await handle_visa_callback(update, context, dependencies.visa_catalog, language)
        await _save_visa_passport(context, user_id, dependencies, previous)
        return
    if data.startswith("language:"):
        selected = normalize_language(data.partition(":")[2])
        await dependencies.users.set_language(user_id, selected)
        await dependencies.audit.record(
            "language.changed", user_id=user_id, payload={"language": selected}
        )
        language = selected
        await query.edit_message_text(
            text(selected, "language_changed"),
            reply_markup=main_menu(
                selected,
                dependencies.web_app_url,
                is_admin=_is_private_admin(update, dependencies),
                    widgets_enabled=_widget_menu_enabled(update, context),
            ),
        )
    elif data == "back":
        context.user_data.pop("price_alert_pending", None)
        await dependencies.audit.record("menu.back", user_id=user_id)
        await query.edit_message_text(
            render_main_menu(
                language,
                update.effective_user.first_name if update.effective_user else None,
            ),
            parse_mode="HTML",
            reply_markup=main_menu(
                language,
                dependencies.web_app_url,
                is_admin=_is_private_admin(update, dependencies),
                    widgets_enabled=_widget_menu_enabled(update, context),
            ),
        )
    elif (
        data in ("menu:airports", "menu:rules")
        or data.startswith(("airports:page:", "airport:"))
    ):
        # Buttons in existing chat history remain clickable after removal from
        # the menu. Route legacy actions to supported services without exposing
        # the hidden features or a "coming soon" placeholder.
        await query.edit_message_text(
            render_main_menu(
                language,
                update.effective_user.first_name if update.effective_user else None,
            ),
            parse_mode="HTML",
            reply_markup=main_menu(
                language,
                dependencies.web_app_url,
                is_admin=_is_private_admin(update, dependencies),
                    widgets_enabled=_widget_menu_enabled(update, context),
            ),
        )
    elif data == "menu:useful":
        if (_widget_menu_enabled(update, context)
                and not context.user_data.get("useful_widget_legacy")):
            if await send_useful_widget(query.message, context,
                    lambda: dependencies.useful_catalog or default_catalog()):
                await dependencies.audit.record("useful.widget.opened", user_id=user_id)
                return
        catalog = dependencies.useful_catalog or default_catalog()
        await dependencies.audit.record(
            "menu.callback", user_id=user_id, payload={"action": "useful"}
        )
        await query.edit_message_text(
            "<b>📚 راهنمای سفر</b>\n"
            "اطلاعات موردنیاز قبل، حین و بعد از سفر را از بخش‌های زیر انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=useful_menu(language, catalog),
        )
    elif data.startswith("useful:"):
        category = data.partition(":")[2]
        catalog = dependencies.useful_catalog or default_catalog()
        if category not in USEFUL_CATEGORY_IDS:
            await query.edit_message_text(
                safe_text(language, "unknown_action"),
                parse_mode="HTML",
                reply_markup=back_menu(language),
            )
        else:
            await dependencies.audit.record(
                "useful.category.viewed", user_id=user_id, payload={"category": category}
            )
            await query.edit_message_text(
                render_useful_category(category),
                parse_mode="HTML",
                reply_markup=useful_category_menu(language, catalog, category),
            )
    elif data == "menu:tickets":
        context.user_data.pop("price_alert_pending", None)
        await dependencies.audit.record("ticket.menu.opened", user_id=user_id)
        if dependencies.cheap_ticket_service is None:
            await query.edit_message_text(
                "سرویس جستجوی بلیط در حال حاضر پیکربندی نشده است.",
                reply_markup=back_menu(language),
            )
        else:
            from .tickets import render_cheap_ticket_intro

            await query.edit_message_text(render_cheap_ticket_intro(), parse_mode="HTML")
            try:
                routes = await dependencies.cheap_ticket_service.routes()
            except ProviderError as exc:
                await _notify_admin(context, exc, update, dependencies)
                await query.message.reply_text(
                    "❌ ارتباط با سایت اطلاعات بلیط برقرار نشد. لطفاً کمی بعد دوباره تلاش کنید.",
                    reply_markup=back_menu(language),
                )
            except Exception as exc:
                LOGGER.exception("cheap_ticket_processing_failed")
                await _notify_admin(context, exc, update, dependencies)
                await query.message.reply_text(
                    "❌ پردازش اطلاعات بلیط با خطا مواجه شد. لطفاً پشتیبانی را مطلع کنید.",
                    reply_markup=back_menu(language),
                )
            else:
                # User-scoped data: the button stores a short index, not a city name.
                # A selected origin reuses this snapshot, without another site crawl.
                context.user_data["ticket_routes"] = routes
                await query.edit_message_text(
                    text(language, "ticket_choose_origin"),
                    reply_markup=ticket_origins_menu(
                        language, [route.origin for route in routes]
                    ),
                )
    elif data == "tickets:menu" or data.startswith("tickets:page:"):
        routes = context.user_data.get("ticket_routes", [])
        if not routes:
            await query.edit_message_text(
                text(language, "ticket_expired"),
                reply_markup=back_menu(language),
            )
        else:
            try:
                page = int(data.removeprefix("tickets:page:")) if data != "tickets:menu" else 0
            except ValueError:
                page = 0
            await query.edit_message_text(
                text(language, "ticket_choose_origin"),
                reply_markup=ticket_origins_menu(
                    language, [route.origin for route in routes], page=page
                ),
            )
    elif data.startswith("tickets:book:"):
        from .tickets import send_ticket_reservation_request

        routes = context.user_data.get("ticket_routes", [])
        try:
            _, _, raw_route_index, raw_destination_index = data.split(":")
            booking_origin_index = int(raw_route_index)
            booking_destination_index = int(raw_destination_index)
            if not 0 <= booking_origin_index < len(routes):
                raise IndexError("Invalid booking route")
            chosen_route = routes[booking_origin_index]
            if not 0 <= booking_destination_index < len(chosen_route.destinations):
                raise IndexError("Invalid booking destination")
        except (ValueError, IndexError):
            await query.message.reply_text(
                text(language, "ticket_expired"),
                reply_markup=back_menu(language),
            )
        else:
            chosen_destination = chosen_route.destinations[booking_destination_index]
            await dependencies.audit.record(
                "ticket.booking.requested",
                user_id=user_id,
                payload={
                    "origin": chosen_route.origin,
                    "destination": chosen_destination.name,
                },
            )
            await send_ticket_reservation_request(
                context.bot,
                query.message,
                chosen_route.origin,
                chosen_destination,
                dependencies.ticket_support_username,
                language,
            )
    elif data.startswith("tickets:origin:"):
        from .tickets import (
            render_cheap_route_chunks,
            render_cheap_ticket_booking_hint,
        )

        routes = context.user_data.get("ticket_routes", [])
        try:
            index = int(data.removeprefix("tickets:origin:"))
        except ValueError:
            index = -1
        if index < 0 or index >= len(routes):
            await query.edit_message_text(
                text(language, "ticket_expired"),
                reply_markup=back_menu(language),
            )
        else:
            route = routes[index]
            await dependencies.audit.record(
                "ticket.origin.selected",
                user_id=user_id,
                payload={"origin": route.origin},
            )
            await query.edit_message_text(
                text(language, "ticket_selected_origin").format(origin=route.origin),
                reply_markup=ticket_origins_menu(
                    language, [item.origin for item in routes], page=index // 16
                ),
            )
            # The bell callback reads the cached ticket_routes snapshot
            # when it is clicked, avoiding a second provider request.
            rich_messages = render_rich_price_tables(
                route, language=language, booking_route_index=index,
                support_username=dependencies.ticket_support_username,
            )
            for rich_message in rich_messages:
                try:
                    await send_rich_price_table_with_badge_fallback(
                        context.bot, query.message.chat_id, rich_message
                    )
                except Exception as exc:
                    # HTTP exceptions can contain the bot token in their URL.
                    LOGGER.warning(
                        "rich_ticket_table_send_failed error_type=%s",
                        type(exc).__name__,
                    )
                    chunks = render_cheap_route_chunks(
                        route, language=language, max_length=2700
                    )
                    booking_hint = render_cheap_ticket_booking_hint(
                        dependencies.ticket_support_username, language
                    )
                    # Keep the disclaimer and four-button keyboard together
                    # under the same fallback fare list message.
                    for i, message in enumerate(chunks):
                        if i == len(chunks) - 1:
                            message = (
                                message.removesuffix(render_ticket_footer(
                                    language, rich=False
                                ))
                                + "\n\n" + booking_hint
                            )
                        await query.message.reply_text(
                            message,
                            parse_mode="HTML",
                            reply_markup=(
                                ticket_result_menu(
                                    language, dependencies.ticket_support_username,
                                    origin_index=index,
                                )
                                if i == len(chunks) - 1 else None
                            ),
                        )
                    break
            # The optional discount report is limited to this origin as well.
            try:
                if find_price_drops([route]):
                    for report in render_rich_price_drop_report([route], language=language):
                        await send_rich_price_table_with_badge_fallback(
                            context.bot, query.message.chat_id, report
                        )
            except Exception:
                LOGGER.exception("rich_ticket_price_drop_report_failed")
                for message in render_price_drop_fallback_chunks([route], language=language):
                    await query.message.reply_text(message, parse_mode="HTML")

    # menu:rules is also disabled by the legacy-callback fallback above.
    elif data == "menu:admin_reports":
        # Reports contain private business data: authorize before collection or transport.
        if not _is_private_admin(update, dependencies):
            await query.edit_message_text(
                safe_text(language, "unknown_action"),
                reply_markup=back_menu(language),
            )
            return
        if dependencies.admin_reports is None:
            await query.edit_message_text(
                "گزارش مدیریتی به دیتابیس متصل نیست.",
                reply_markup=main_menu(
                    language, dependencies.web_app_url, is_admin=True,
                    widgets_enabled=_widget_menu_enabled(update, context),
                ),
            )
            return
        try:
            report = await dependencies.admin_reports.collect()
        except Exception as exc:
            LOGGER.exception("admin_report_generation_failed")
            await _notify_admin(context, exc, update, dependencies)
            await query.message.reply_text(
                "خطا در تهیه گزارش. جزئیات فنی برای مدیر ارسال شد."
            )
            return
        try:
            rich = render_rich_admin_report(report)
            await send_rich_price_table(context.bot, update.effective_chat.id, rich)
        except Exception as exc:
            # The native rich endpoint may not be supported. Never expose bot tokens in logs.
            LOGGER.warning("admin_report_rich_failed error_type=%s", type(exc).__name__)
            try:
                for part in render_admin_report_fallback(report):
                    await query.message.reply_text(
                        part, parse_mode="HTML", disable_web_page_preview=True
                    )
            except Exception as fallback_exc:
                LOGGER.exception("admin_report_fallback_failed")
                await _notify_admin(context, fallback_exc, update, dependencies)
                await query.message.reply_text(
                    "خطا در ارسال گزارش. جزئیات فنی برای مدیر ارسال شد."
                )
                return
        # User identities are available only after the private-admin gate above.
        # Send the extra report separately so the existing aggregate Rich
        # Message stays complete and small even with many registered users.
        if getattr(report, "user_activity", ()):
            rich_pages = render_rich_user_activity_reports(report)
            fallback_pages = render_user_activity_fallback(report)
            for rich_page, fallback_page in zip(rich_pages, fallback_pages, strict=True):
                try:
                    await send_rich_price_table(
                        context.bot, update.effective_chat.id, rich_page
                    )
                except Exception as exc:
                    LOGGER.warning(
                        "admin_user_activity_rich_failed error_type=%s",
                        type(exc).__name__,
                    )
                    try:
                        await query.message.reply_text(
                            fallback_page, parse_mode="HTML",
                            disable_web_page_preview=True,
                        )
                    except Exception as fallback_exc:
                        LOGGER.exception("admin_user_activity_fallback_failed")
                        await _notify_admin(context, fallback_exc, update, dependencies)
                        await query.message.reply_text(
                            "خطا در ارسال گزارش کاربران؛ جزئیات برای مدیر ارسال شد."
                        )
                        break
        await dependencies.audit.record("admin.report.viewed", user_id=user_id)
    elif data == "menu:support":
        await dependencies.audit.record("support.opened", user_id=user_id)
        await query.edit_message_text(
            render_support_message(language, dependencies.ticket_support_username),
            parse_mode="HTML",
            reply_markup=support_menu(language, dependencies.ticket_support_username),
        )
    elif data == "menu:settings":
        await query.edit_message_text(
            render_language_prompt(language), parse_mode="HTML", reply_markup=language_menu()
        )
    elif data.startswith("menu:"):
        await dependencies.audit.record(
            "menu.callback", user_id=user_id, payload={"action": data[5:]}
        )
        await query.edit_message_text(
            safe_text(language, "menu"), parse_mode="HTML", reply_markup=back_menu(language)
        )
    else:
        await query.edit_message_text(
            safe_text(language, "unknown_action"),
            parse_mode="HTML",
            reply_markup=back_menu(language),
        )


async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    dependencies: TelegramDependencies | None = None,
) -> None:
    if dependencies is not None and update.message is not None:
        if context.user_data.get("price_alert_pending") and dependencies.price_alert_service:
            user_id, language = await _user_language(update, dependencies)
            if await handle_alert_text(
                update, context, dependencies.price_alert_service, user_id, language
            ):
                return
        if context.user_data.get("visa_search_mode"):
            _user_id, language = await _user_language(update, dependencies)
            if await visa_search_text(
                update, context, dependencies.visa_catalog, language
            ):
                return
    if update.message is None:
        return
    # Unstructured text is not a chat command. Avoid unsolicited replies in groups.
    if getattr(getattr(update, "effective_chat", None), "type", None) != "private":
        return
    language = "fa"
    if dependencies is not None:
        _user_id, language = await _user_language(update, dependencies)
    await update.message.reply_text(
        text(language, "free_text_hint"),
        reply_markup=main_menu(
            language,
            dependencies.web_app_url if dependencies is not None else None,
            is_admin=(
                _is_private_admin(update, dependencies)
                if dependencies is not None else False
            ),
            widgets_enabled=_widget_menu_enabled(update, context),
        ),
    )


async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.inline_query:
        await update.inline_query.answer([])




async def visa_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    dependencies: TelegramDependencies,
) -> None:
    user_id, language = await _user_language(update, dependencies)
    await dependencies.audit.record("visa.command", user_id=user_id)
    if (not getattr(context, "args", None) and update.message is not None
            and _widget_menu_enabled(update, context)):
        if await send_visa_widget(update.message, context, dependencies.visa_catalog,
            dependencies.visa_watch_service, dependencies.users, user_id, language):
            return
    await _load_visa_passport(context, user_id, dependencies)
    previous = context.user_data["visa_passport"]
    await visa_command(update, context, dependencies.visa_catalog, language)
    await _save_visa_passport(context, user_id, dependencies, previous)


async def visa_list_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    dependencies: TelegramDependencies,
) -> None:
    user_id, language = await _user_language(update, dependencies)
    await dependencies.audit.record("visa.list.command", user_id=user_id)
    if update.message is None:
        return
    catalog = dependencies.visa_catalog
    if catalog is None or not await catalog.ready():
        from .visa_presentation import tr
        await update.message.reply_text(tr(language, "empty"))
        return
    await _load_visa_passport(context, user_id, dependencies)
    previous = context.user_data["visa_passport"]
    args = context.args or []
    code = (args[0] if args else previous).upper()
    codes = {country.code for country in await catalog.countries()}
    if code not in codes:
        from .visa_presentation import tr
        await update.message.reply_text(tr(language, "choose_passport"))
        return
    context.user_data["visa_passport"] = code
    await _save_visa_passport(context, user_id, dependencies, previous)
    from .visa_presentation import groups_keyboard, tr
    await update.message.reply_text(
        f"<b>{tr(language, 'list')}</b> — <code>{code}</code>",
        parse_mode="HTML",
        reply_markup=groups_keyboard(language, await catalog.distribution(code)),
    )


async def visa_cancel_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    dependencies: TelegramDependencies,
) -> None:
    if context.user_data.pop("price_alert_pending", None) is not None:
        if update.message:
            _, language = await _user_language(update, dependencies)
            await update.message.reply_text(
                word(language, "cancelled"),
                reply_markup=menu_keyboard(language),
            )
        return
    context.user_data.pop("visa_search_mode", None)
    if update.message:
        user_id, language = await _user_language(update, dependencies)
        await dependencies.audit.record("visa.search.cancelled", user_id=user_id)
        await _load_visa_passport(context, user_id, dependencies)
        await open_visa_menu(
            update, context, dependencies.visa_catalog, language, edit=False
        )


async def visa_watch_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    if update.message is None:
        return
    user_id, language = await _user_language(update, dependencies)
    if (
        getattr(update, "effective_chat", None) is None
        or update.effective_chat.type != "private"
    ):
        await update.message.reply_text(visa_watch_text(language, "private"))
        return
    if dependencies.visa_watch_service is None:
        await update.message.reply_text(visa_watch_text(language, "unavailable"))
        return
    await show_watches(
        update.message, dependencies.visa_watch_service, user_id, language,
        edit=False,
    )
    await dependencies.audit.record("visa.watch.menu", user_id=user_id)


async def visa_sync_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    """Manual visa refresh; strictly admin-only in the configured private chat."""
    if not _is_private_admin(update, dependencies):
        if update.message:
            await update.message.reply_text("این دستور فقط برای مدیر ربات است.")
        return
    if not update.message:
        return
    if dependencies.visa_sync_service is None:
        await update.message.reply_text("سرویس به‌روزرسانی ویزا فعال نیست.")
        return
    progress = await update.message.reply_text(
        "در حال بررسی و دریافت اطلاعات ویزا از TravelRequirements.info ..."
    )
    try:
        result = await dependencies.visa_sync_service.sync()
    except Exception as exc:
        LOGGER.exception("manual_visa_sync_failed")
        await progress.edit_text(
            "به‌روزرسانی ناموفق بود؛ داده قبلی حفظ شد.\n"
            f"علت: {type(exc).__name__}: {str(exc)[:240]}\n"
            "منبع: https://travelrequirements.info/data/index.json"
        )
        return
    await progress.edit_text(
        result.render(manual=True, html=True),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    if dependencies.visa_watch_service is not None and result.alerts_queued:
        try:
            await deliver_watch_notifications(
                context.bot, dependencies.visa_watch_service, dependencies.users
            )
        except Exception:
            LOGGER.exception("manual_visa_change_notification_delivery_failed")


async def alerts_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    if update.message is None:
        return
    user_id, language = await _user_language(update, dependencies)
    await dependencies.audit.record("price_alerts.opened", user_id=user_id)
    if dependencies.price_alert_service is None:
        await update.message.reply_text(word(language, "unavailable"))
        return
    alerts = await dependencies.price_alert_service.list_user_alerts(user_id)
    bot = getattr(context, "bot", None)
    chat_id = getattr(update.message, "chat_id", None)
    if bot is not None and chat_id is not None:
        try:
            await send_rich_alerts(bot, chat_id, alerts, language)
        except Exception as exc:
            # Telegram HTTP exceptions may include the secret bot token.
            LOGGER.warning(
                "price_alert_command_rich_failed error_type=%s",
                type(exc).__name__,
            )
        else:
            return
    from .price_alerts import _alert_fallback_pages

    for message, keyboard in _alert_fallback_pages(alerts, language):
        await update.message.reply_text(
            message, parse_mode="HTML", reply_markup=keyboard,
        )


async def airports_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    """Open the 29-airport guide without leaving the private Telegram chat."""
    if update.message is None:
        return
    if not _widget_menu_enabled(update, context):
        await update.message.reply_text("راهنمای تعاملی فقط در چت خصوصی تلگرام فعال است.")
        return
    user_id, _language = await _user_language(update, dependencies)
    await dependencies.audit.record("airport.widget.opened", user_id=user_id)
    await send_airport_widget(
        update.message, context.bot, _airport_store(dependencies), dependencies.web_app_url
    )


async def chart_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    """Choose a recorded origin/destination and send its actual price chart."""
    if update.message is None:
        return
    if not _widget_menu_enabled(update, context):
        await update.message.reply_text("نمودار فقط در چت خصوصی تلگرام فعال است.")
        return
    user_id, _language = await _user_language(update, dependencies)
    await dependencies.audit.record("ticket.chart.opened", user_id=user_id)
    await open_chart_picker(
        update.message, context.bot,
        getattr(dependencies.cheap_ticket_service, "price_history", None),
        context.user_data,
    )


async def fare_widget_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    """Show the same widget without needing the inline menu."""
    if update.message is None:
        return
    if getattr(context.bot, "platform", "telegram") == "bale":
        await update.message.reply_text("ویجت HTML فعلاً فقط در تلگرام فعال است.")
        return
    user_id, _language = await _user_language(update, dependencies)
    await dependencies.audit.record("ticket.widget.opened", user_id=user_id)
    await send_fare_widget(update.message, context.bot, dependencies.cheap_ticket_service)


async def checklist_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    """Open the user's saved private travel checklist without a Mini App."""
    if update.message is None:
        return
    if getattr(context.bot, "platform", "telegram") == "bale":
        await update.message.reply_text("چک‌لیست تعاملی فقط در تلگرام فعال است.")
        return
    user_id, _language = await _user_language(update, dependencies)
    await dependencies.audit.record("checklist.opened", user_id=user_id)
    await send_checklist_widget(update.message, context.bot, dependencies.checklist_service)


async def _open_help_service(
    service: str, user_id: int, context: ContextTypes.DEFAULT_TYPE,
    dependencies: TelegramDependencies,
) -> None:
    """Launch existing bot flows only after a validated private help query."""
    bot = context.bot
    msg = PrivateChatMessage(bot, user_id)
    # widget_query supplies the Telegram account ID, not the internal users.id.
    # Preferences and audit events must use the internal database primary key.
    registered = await dependencies.users.get_by_telegram_id(user_id)
    if registered is None:
        raise ValueError("Help widget user is not registered")
    database_user_id = registered.id
    language = normalize_language(
        await dependencies.users.get_language(database_user_id)
    )
    await dependencies.audit.record(
        "user.help.service", user_id=database_user_id, payload={"service": service},
    )

    if service == "fares":
        await send_fare_widget(msg, bot, dependencies.cheap_ticket_service)
        return
    if service == "airports":
        await send_airport_widget(
            msg, bot, _airport_store(dependencies), dependencies.web_app_url,
        )
        return
    if service == "checklist":
        await send_checklist_widget(msg, bot, dependencies.checklist_service)
        return

    # Unknown widget updates in PTB <=22 lack effective_user, and consequently
    # context.user_data. Resolve the verified sender's own per-user storage.
    application = getattr(context, "application", None)
    user_data = (
        application.user_data[user_id]
        if application is not None else {}
    )
    private_context = SimpleNamespace(bot=bot, user_data=user_data, args=[])
    user = SimpleNamespace(
        id=user_id, username=None, first_name="", last_name=None,
    )
    message_update = SimpleNamespace(
        message=msg, effective_user=user, effective_chat=msg.chat,
    )
    if service == "chart":
        await open_chart_picker(
            msg, bot,
            getattr(dependencies.cheap_ticket_service, "price_history", None),
            user_data,
        )
    elif service == "visa":
        await _load_visa_passport(private_context, database_user_id, dependencies)
        await open_visa_menu(
            message_update, private_context, dependencies.visa_catalog, language,
            edit=False,
        )
    elif service == "alerts":
        await alerts_command_handler(message_update, private_context, dependencies)
    elif service == "visa_watch":
        await visa_watch_handler(message_update, private_context, dependencies)
    elif service == "visa_list":
        await visa_list_handler(message_update, private_context, dependencies)
    elif service == "language":
        await msg.reply_text(
            render_language_prompt(language), parse_mode="HTML",
            reply_markup=language_menu(),
        )
    elif service == "start":
        await msg.reply_text(
            render_main_menu(language), parse_mode="HTML",
            reply_markup=main_menu(
                language, dependencies.web_app_url, widgets_enabled=True,
            ),
        )
    elif service == "support":
        await msg.reply_text(
            render_support_message(language, dependencies.ticket_support_username),
            parse_mode="HTML",
            reply_markup=support_menu(language, dependencies.ticket_support_username),
        )


async def _all_widget_queries(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    raw = update.api_kwargs.get("widget_query")
    action = raw.get("data") if isinstance(raw, dict) else None
    if isinstance(action, str) and action.startswith("uf:"):
        await handle_useful_widget_query(update, context,
            lambda: dependencies.useful_catalog or default_catalog())
    elif isinstance(action, str) and action.startswith("vi:"):
        async def open_existing(command, owner):
            service = {"legacy": "visa", "watches": "visa_watch", "home": "start"}[command]
            await _open_help_service(service, owner, context, dependencies)
        await handle_visa_widget_query(update, context, dependencies.visa_catalog,
            dependencies.visa_watch_service, dependencies.users, open_existing)
    elif isinstance(action, str) and action.startswith("hp:"):
        await handle_help_widget_query(
            update, context,
            lambda service, user_id: _open_help_service(service, user_id, context, dependencies),
        )
    elif isinstance(action, str) and action.startswith("ap:"):
        await handle_airport_widget_query(update, context, _airport_store(dependencies))
    elif isinstance(action, str) and action.startswith("cl:"):
        await handle_checklist_query(update, context, dependencies.checklist_service)
    else:
        await widget_query_handler(update, context, dependencies.cheap_ticket_service)


async def experiences_command_handler(update, context, dependencies):
    if update.message is None:
        return
    args = getattr(context, "args", None) or []
    await show_experiences(update.message, dependencies.experience_service,
                           dependencies.web_app_url, target=args[0] if args else "")


async def useful_command_handler(update, context, dependencies, *, legacy=False):
    if update.message is None:
        return
    if isinstance(getattr(context, "user_data", None), dict):
        context.user_data["useful_widget_legacy"] = legacy
    _, language = await _user_language(update, dependencies)
    if not legacy and _widget_menu_enabled(update, context):
        if await send_useful_widget(update.message, context,
                lambda: dependencies.useful_catalog or default_catalog()):
            return
    catalog = dependencies.useful_catalog or default_catalog()
    await update.message.reply_text(
        "<b>📚 راهنمای سفر</b>\n"
        "اطلاعات موردنیاز قبل، حین و بعد از سفر را از بخش‌های زیر انتخاب کنید:",
        parse_mode="HTML", reply_markup=useful_menu(language, catalog),
    )


def register_handlers(application: Application, dependencies: TelegramDependencies) -> None:
    """Register the shell handlers on an existing Telegram application."""
    application.add_handler(
        TypeHandler(Update, lambda u, c: user_activity_handler(u, c, dependencies)), group=1
    )
    application.add_handler(
        CommandHandler("useful", lambda u,c: useful_command_handler(u,c,dependencies))
    )
    application.add_handler(
        CommandHandler("useful_legacy",
            lambda u,c: useful_command_handler(u,c,dependencies,legacy=True))
    )
    application.add_handler(
        CommandHandler("experiences", lambda u,c: experiences_command_handler(u,c,dependencies))
    )
    application.add_handler(
        CommandHandler("visa", lambda u, c: visa_handler(u, c, dependencies))
    )
    application.add_handler(
        CommandHandler("visa_list", lambda u, c: visa_list_handler(u, c, dependencies))
    )
    application.add_handler(
        CommandHandler("cancel", lambda u, c: visa_cancel_handler(u, c, dependencies))
    )
    application.add_handler(
        CommandHandler("visa_sync", lambda u, c: visa_sync_handler(u, c, dependencies))
    )
    application.add_handler(
        CommandHandler("visa_watch", lambda u, c: visa_watch_handler(u, c, dependencies))
    )
    application.add_handler(CommandHandler("start", lambda u, c: start_handler(u, c, dependencies)))
    application.add_handler(CommandHandler("help", lambda u, c: help_handler(u, c, dependencies)))
    if getattr(application.bot, "platform", "telegram") != "bale":
        application.add_handler(
            CommandHandler("airports", lambda u, c: airports_command_handler(u, c, dependencies))
        )
        application.add_handler(
            CommandHandler("fares", lambda u, c: fare_widget_command_handler(u, c, dependencies))
        )
        application.add_handler(
            CommandHandler("chart", lambda u, c: chart_command_handler(u, c, dependencies))
        )
        application.add_handler(
            CommandHandler(
                "checklist", lambda u, c: checklist_command_handler(u, c, dependencies)
            )
        )
        # PTB <=22 preserves unknown Bot API fields under Update.api_kwargs.
        application.add_handler(
            TypeHandler(
                Update,
                lambda u, c: _all_widget_queries(u, c, dependencies),
            ),
            group=2,
        )
    application.add_handler(
        CommandHandler("alerts", lambda u, c: alerts_command_handler(u, c, dependencies))
    )
    application.add_handler(
        CommandHandler("language", lambda u, c: language_handler(u, c, dependencies))
    )
    application.add_handler(CallbackQueryHandler(lambda u, c: callback_handler(u, c, dependencies)))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            lambda u, c: message_handler(u, c, dependencies),
        )
    )
    application.add_handler(InlineQueryHandler(inline_handler))
    application.add_error_handler(lambda u, c: error_handler(u, c, dependencies))
