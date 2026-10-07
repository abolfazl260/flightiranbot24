"""Telegram handlers kept free of provider and SQL details."""

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
from flightiran.modules.airport.catalog import AirportCatalog
from flightiran.modules.currency.service import CurrencyService
from flightiran.modules.flight_tracking.domain import FlightSearchResult, FlightSearchStatus
from flightiran.modules.flight_tracking.service import FlightService

from .keyboards import back_menu, language_menu, main_menu
from .localization import normalize_language, safe_text, text
from .renderers import render_language_prompt, render_main_menu


@dataclass(frozen=True)
class TelegramDependencies:
    users: UserRepository
    audit: AuditRepository
    flight_service: FlightService | None = None
    currency_service: CurrencyService | None = None
    web_app_url: str | None = None
    airport_catalog: AirportCatalog | None = None


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
            render_main_menu(language),
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
            render_main_menu(language),
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
    elif data == "menu:tickets":
        await query.edit_message_text(
            "برای جستجوی بلیط، ابتدا مسیر و تاریخ را آماده کنید.\nمثال: IKA → FRA",
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
    query = " ".join(context.args or []) if context else None
    result = (
        await dependencies.flight_service.search(query)
        if dependencies.flight_service
        else FlightSearchResult(FlightSearchStatus.DISABLED, message="disabled")
    )
    from .flight import render_flight_result

    message, keyboard = render_flight_result(result)
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
