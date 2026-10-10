"""Telegram handlers kept free of provider and SQL details."""

import logging
import traceback
from dataclasses import dataclass

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
    send_rich_price_table_with_badge_fallback,
)
from flightiran.modules.admin.reports import BotReportRepository
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.service import CheapTicketService
from flightiran.modules.useful_content import UsefulContentCatalog, default_catalog
from flightiran.modules.visa.catalog import VisaCatalogService
from flightiran.modules.visa.sync import VisaSyncService
from flightiran.modules.visa.watch import VisaWatchService

from .admin_report import render_admin_report
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
from .support import render_support_message
from .useful_content import (
    USEFUL_CATEGORY_IDS,
    render_useful_category,
    useful_category_menu,
    useful_menu,
)
from .visa_flow import (
    handle_visa_callback,
    open_visa_menu,
    visa_command,
    visa_search_text,
)
from .visa_watches import deliver_watch_notifications, handle_watch_callback, show_watches
from .visa_watches import word as visa_watch_text

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramDependencies:
    users: UserRepository
    audit: AuditRepository
    web_app_url: str | None = None
    airport_catalog: AirportCatalog | None = None
    useful_catalog: UsefulContentCatalog | None = None
    cheap_ticket_service: CheapTicketService | None = None
    price_alert_service: PriceAlertService | None = None
    ticket_support_username: str = DEFAULT_SUPPORT_USERNAME
    admin_chat_id: int = 106056586
    admin_reports: BotReportRepository | None = None
    visa_sync_service: VisaSyncService | None = None
    visa_catalog: VisaCatalogService | None = None
    visa_watch_service: VisaWatchService | None = None


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
    """Send a compact runtime error report to the configured Telegram admin."""

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
    if update.message:
        await update.message.reply_text(
            render_main_menu(language, telegram_user.first_name),
            parse_mode="HTML",
            reply_markup=main_menu(
                language,
                dependencies.web_app_url,
                is_admin=_is_private_admin(update, dependencies),
            ),
        )
    if is_new:
        await dependencies.audit.record("user.registered", user_id=registered.id)
        if context is not None and getattr(context, "bot", None) is not None:
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
        await update.message.reply_text(
            render_help(language, dependencies.ticket_support_username),
            parse_mode="HTML",
            reply_markup=main_menu(
                language,
                dependencies.web_app_url,
                is_admin=_is_private_admin(update, dependencies),
            ),
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
            ),
        )
    elif data == "menu:airports" and dependencies.airport_catalog:
        from .airport import airport_keyboard

        await dependencies.audit.record(
            "menu.callback", user_id=user_id, payload={"action": "airports"}
        )
        await query.edit_message_text(
            "<b>فرودگاه را انتخاب کنید</b>",
            parse_mode="HTML",
            reply_markup=airport_keyboard(dependencies.airport_catalog.all()),
        )
    elif data.startswith("airports:page:") and dependencies.airport_catalog:
        from .airport import airport_keyboard

        page = int(data.rsplit(":", 1)[1])
        await query.edit_message_text(
            "<b>فرودگاه را انتخاب کنید</b>",
            parse_mode="HTML",
            reply_markup=airport_keyboard(dependencies.airport_catalog.all(), page=page),
        )
    elif data.startswith("airport:") and dependencies.airport_catalog:
        airport = dependencies.airport_catalog.get(data.partition(":")[2])
        if airport is None:
            await query.edit_message_text("فرودگاه پیدا نشد.", reply_markup=back_menu(language))
        else:
            await query.edit_message_text(
                f"<b>{airport.display_name(language)}</b>\n"
                f"کد: {airport.code}\nکشور: {airport.country}\n"
                f"منطقه زمانی: {airport.timezone}",
                parse_mode="HTML",
                reply_markup=back_menu(language),
            )
    elif data == "menu:useful":
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

    elif data == "menu:rules":
        await query.edit_message_text(
            "این بخش به منبع رسمی نیاز دارد و از طریق منوی ربات قابل جستجو است.",
            reply_markup=back_menu(language),
        )
    elif data == "menu:admin_reports":
        # Never trust a visible/forged callback as proof of authorization.
        # Reports are sent only in the configured admin's private chat.
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
                    language, dependencies.web_app_url, is_admin=True
                ),
            )
            return
        await query.edit_message_text(
            "⏳ در حال تهیه گزارش جامع ربات از داده‌های ثبت‌شده...",
            reply_markup=main_menu(
                language, dependencies.web_app_url, is_admin=True
            ),
        )
        try:
            report = await dependencies.admin_reports.collect()
            for part in render_admin_report(report):
                await query.message.reply_text(part, parse_mode="HTML")
        except Exception as exc:
            LOGGER.exception("admin_report_generation_failed")
            await _notify_admin(context, exc, update, dependencies)
            await query.message.reply_text(
                "خطا در تهیه گزارش. جزئیات فنی برای مدیر ارسال شد."
            )
        else:
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
    if update.message:
        await update.message.reply_text("OK")


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


def register_handlers(application: Application, dependencies: TelegramDependencies) -> None:
    """Register the shell handlers on an existing Telegram application."""
    application.add_handler(
        TypeHandler(Update, lambda u, c: user_activity_handler(u, c, dependencies)), group=1
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
