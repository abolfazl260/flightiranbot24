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

from .keyboards import back_menu, language_menu, main_menu
from .localization import normalize_language, safe_text, text
from .renderers import render_language_prompt, render_main_menu


@dataclass(frozen=True)
class TelegramDependencies:
    users: UserRepository
    audit: AuditRepository


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
            render_main_menu(language), parse_mode="HTML", reply_markup=main_menu(language)
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
            text(selected, "language_changed"), reply_markup=main_menu(selected)
        )
    elif data == "back":
        await dependencies.audit.record("menu.back", user_id=user_id)
        await query.edit_message_text(
            render_main_menu(language), parse_mode="HTML", reply_markup=main_menu(language)
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


def register_handlers(application: Application, dependencies: TelegramDependencies) -> None:
    """Register the shell handlers on an existing Telegram application."""
    application.add_handler(CommandHandler("start", lambda u, c: start_handler(u, c, dependencies)))
    application.add_handler(
        CommandHandler("language", lambda u, c: language_handler(u, c, dependencies))
    )
    application.add_handler(CallbackQueryHandler(lambda u, c: callback_handler(u, c, dependencies)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(InlineQueryHandler(inline_handler))
