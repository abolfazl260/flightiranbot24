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
    filters,
)

from flightiran.db.repositories import AuditRepository, UserRepository
from flightiran.infrastructure.http.errors import ProviderError
from flightiran.interfaces.telegram.rich_tickets import (
    render_rich_price_tables,
    send_rich_price_table,
)
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.currency.service import CurrencyService
from flightiran.modules.flight_tracking.domain import FlightSearchResult, FlightSearchStatus
from flightiran.modules.flight_tracking.service import FlightService
from flightiran.modules.tickets.service import CheapTicketService
from flightiran.modules.useful_content import UsefulContentCatalog, default_catalog

from .keyboards import back_menu, language_menu, main_menu
from .localization import normalize_language, safe_text, text
from .renderers import render_help, render_language_prompt, render_main_menu
from .useful_content import (
    USEFUL_CATEGORY_IDS,
    render_useful_category,
    useful_category_menu,
    useful_menu,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramDependencies:
    users: UserRepository
    audit: AuditRepository
    flight_service: FlightService | None = None
    currency_service: CurrencyService | None = None
    web_app_url: str | None = None
    airport_catalog: AirportCatalog | None = None
    useful_catalog: UsefulContentCatalog | None = None
    cheap_ticket_service: CheapTicketService | None = None
    ticket_support_username: str = "@vlansupport"
    admin_chat_id: int = 106056586


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
    await _notify_admin(context, error, update, dependencies)


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


async def start_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    user_id, language = await _user_language(update, dependencies)
    await dependencies.audit.record("user.start", user_id=user_id)
    if update.message:
        await update.message.reply_text(
            render_main_menu(
                language,
                update.effective_user.first_name if update.effective_user else None,
            ),
            parse_mode="HTML",
            reply_markup=main_menu(language, dependencies.web_app_url),
        )


async def help_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    user_id, language = await _user_language(update, dependencies)
    await dependencies.audit.record("user.help", user_id=user_id)
    if update.message:
        await update.message.reply_text(
            render_help(language),
            parse_mode="HTML",
            reply_markup=main_menu(language, dependencies.web_app_url),
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
    if data.startswith("language:"):
        selected = normalize_language(data.partition(":")[2])
        await dependencies.users.set_language(user_id, selected)
        await dependencies.audit.record(
            "language.changed", user_id=user_id, payload={"language": selected}
        )
        language = selected
        await query.edit_message_text(
            text(selected, "language_changed"),
            reply_markup=main_menu(selected, dependencies.web_app_url),
        )
    elif data == "back":
        await dependencies.audit.record("menu.back", user_id=user_id)
        await query.edit_message_text(
            render_main_menu(
                language,
                update.effective_user.first_name if update.effective_user else None,
            ),
            parse_mode="HTML",
            reply_markup=main_menu(language, dependencies.web_app_url),
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
    elif data == "menu:flights":
        await query.edit_message_text(
            "برای جستجوی پرواز، شماره را ارسال کنید:\n<code>/flight KLM561</code>",
            parse_mode="HTML",
            reply_markup=back_menu(language),
        )
    elif data == "menu:currency" and dependencies.currency_service:
        from .currency import render_quotes

        await query.edit_message_text(
            render_quotes(await dependencies.currency_service.quotes()),
            parse_mode="HTML",
            reply_markup=back_menu(language),
        )
    elif data == "menu:currency":
        await query.edit_message_text(
            "سرویس نرخ ارز هنوز پیکربندی نشده است. مقدار CURRENCY_PROVIDER_URL را تنظیم کنید.",
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
        from .tickets import (
            render_cheap_route_chunks,
            render_cheap_ticket_booking_hint,
            render_cheap_ticket_intro,
        )

        if dependencies.cheap_ticket_service is None:
            await query.edit_message_text(
                "سرویس جستجوی بلیط در حال حاضر پیکربندی نشده است.",
                reply_markup=back_menu(language),
            )
        else:
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
                for route in routes:
                    for rich_message in render_rich_price_tables(route):
                        try:
                            await send_rich_price_table(
                                context.bot,
                                query.message.chat_id,
                                rich_message,
                            )
                        except Exception:
                            LOGGER.exception("rich_ticket_table_send_failed")
                            for message in render_cheap_route_chunks(route):
                                await query.message.reply_text(
                                    message, parse_mode="HTML"
                                )
                            break
                await query.message.reply_text(
                    render_cheap_ticket_booking_hint(dependencies.ticket_support_username),
                    parse_mode="HTML",
                    reply_markup=back_menu(language),
                )
    elif data in {"menu:visa", "menu:rules"}:
        await query.edit_message_text(
            "این بخش به منبع رسمی نیاز دارد و از طریق منوی ربات قابل جستجو است.",
            reply_markup=back_menu(language),
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


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("OK")


async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.inline_query:
        await update.inline_query.answer([])


async def flight_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    _user_id, language = await _user_language(update, dependencies)
    query = " ".join(context.args or []) if context else None
    result = (
        await dependencies.flight_service.search(query)
        if dependencies.flight_service
        else FlightSearchResult(FlightSearchStatus.DISABLED, message="disabled")
    )
    from .flight import render_flight_result

    message, keyboard = render_flight_result(result, language)
    if update.message:
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=keyboard)


async def price_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, dependencies: TelegramDependencies
) -> None:
    from .currency import render_quotes

    quotes = await dependencies.currency_service.quotes() if dependencies.currency_service else []
    if update.message:
        await update.message.reply_text(render_quotes(quotes), parse_mode="HTML")


def register_handlers(application: Application, dependencies: TelegramDependencies) -> None:
    """Register the shell handlers on an existing Telegram application."""
    application.add_handler(CommandHandler("start", lambda u, c: start_handler(u, c, dependencies)))
    application.add_handler(CommandHandler("help", lambda u, c: help_handler(u, c, dependencies)))
    application.add_handler(
        CommandHandler("language", lambda u, c: language_handler(u, c, dependencies))
    )
    application.add_handler(
        CommandHandler("flight", lambda u, c: flight_handler(u, c, dependencies))
    )
    application.add_handler(CommandHandler("price", lambda u, c: price_handler(u, c, dependencies)))
    application.add_handler(CallbackQueryHandler(lambda u, c: callback_handler(u, c, dependencies)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(InlineQueryHandler(inline_handler))
    application.add_error_handler(lambda u, c: error_handler(u, c, dependencies))
