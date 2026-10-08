"""Interactive Telegram visa browsing, search, reports and direct commands."""

from __future__ import annotations

import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from flightiran.modules.visa.catalog import Country, VisaCatalogService, VisaDetail

from .rich_tickets import send_rich_price_table
from .visa_presentation import (
    country_keyboard,
    country_label,
    detail_keyboard,
    groups_keyboard,
    home_keyboard,
    listing_keyboard,
    passport_keyboard,
    render_overview,
    render_rich_report,
    render_section,
    section_keyboard,
    status_label,
    tr,
)

LOGGER = logging.getLogger(__name__)


async def _country_catalog(service: VisaCatalogService) -> list[Country]:
    return await service.countries()


def _context_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data


def _find_country(countries: list[Country], code: str) -> Country | None:
    return next((item for item in countries if item.code == code.upper()), None)


def _matches(countries: list[Country], phrase: str, language: str) -> list[Country]:
    clean = phrase.strip().casefold()
    if not clean:
        return []
    results = [
        country for country in countries
        if clean in country.code.casefold()
        or clean in country.name.casefold()
        or clean in country_label(country.code, country.name, language).casefold()
    ]
    return results[:28]


async def _detail(
    service: VisaCatalogService, passport: str, destination: str
) -> VisaDetail | None:
    return await service.detail(passport, destination)


async def _show_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: VisaCatalogService,
    language: str,
    *,
    edit: bool,
) -> None:
    data = _context_data(context)
    passport = data.get("visa_passport")
    destination = data.get("visa_destination")
    if not passport or not destination:
        rendered = escape(tr(language, "choose_passport"))
        keyboard = home_keyboard(language)
    else:
        detail = await _detail(service, passport, destination)
        if detail is None:
            rendered = escape(tr(language, "missing"))
            keyboard = passport_keyboard(language)
        else:
            names = await _country_catalog(service)
            passport_country = _find_country(names, passport)
            rendered = render_overview(
                detail,
                language,
                passport_name=passport_country.name if passport_country else passport,
                residence=data.get("visa_residence"),
                purpose=data.get("visa_purpose", "tourism"),
            )
            keyboard = detail_keyboard(language)
    if edit:
        await update.callback_query.edit_message_text(
            rendered, parse_mode="HTML", reply_markup=keyboard,
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text(
            rendered, parse_mode="HTML", reply_markup=keyboard,
            disable_web_page_preview=True,
        )


async def open_visa_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: VisaCatalogService | None,
    language: str,
    *,
    edit: bool = True,
) -> None:
    if service is None or not await service.ready():
        message = tr(language, "empty")
        keyboard = home_keyboard(language)
    else:
        message = f"<b>{escape(tr(language, 'title'))}</b>\n\n{escape(tr(language, 'intro'))}"
        keyboard = home_keyboard(language)
    if edit:
        await update.callback_query.edit_message_text(
            message, parse_mode="HTML", reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            message, parse_mode="HTML", reply_markup=keyboard,
        )


async def handle_visa_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: VisaCatalogService | None,
    language: str,
) -> None:
    """Handle only visa:* namespace; caller has already answered callback."""
    query = update.callback_query
    if query is None:
        return
    if service is None or not await service.ready():
        await query.edit_message_text(
            escape(tr(language, "empty")), reply_markup=home_keyboard(language)
        )
        return
    data = _context_data(context)
    action = query.data or ""
    countries: list[Country]
    if action == "visa:home":
        await open_visa_menu(update, context, service, language)
        return

    if action.startswith("visa:pick:"):
        parts = action.split(":")
        if len(parts) != 4 or parts[2] not in {"p", "d", "r"} or not parts[3].isdigit():
            await query.edit_message_text(escape(tr(language, "unknown")))
            return
        mode, page = parts[2], min(int(parts[3]), 500)
        countries = await _country_catalog(service)
        prompt = {
            "p": "choose_passport", "d": "choose_destination", "r": "residence",
        }[mode]
        await query.edit_message_text(
            f"<b>{escape(tr(language, prompt))}</b>\n"
            f"{escape(tr(language, 'search_hint'))}",
            parse_mode="HTML",
            reply_markup=country_keyboard(countries, language, purpose=mode, page=page),
        )
        return

    if action.startswith("visa:search:"):
        mode = action.partition("visa:search:")[2]
        if mode not in {"p", "d", "r"}:
            return
        data["visa_search_mode"] = mode
        await query.edit_message_text(
            f"<b>{escape(tr(language, 'search'))}</b>\n"
            f"{escape(tr(language, 'search_hint'))}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(tr(language, "back"), callback_data=f"visa:pick:{mode}:0")]
            ]),
        )
        return

    if action == "visa:r:clear":
        data.pop("visa_residence", None)
        await _show_result(update, context, service, language, edit=True)
        return

    if action.startswith(("visa:p:", "visa:d:", "visa:r:")):
        mode, code = action.split(":")[1:]
        countries = await _country_catalog(service)
        country = _find_country(countries, code)
        if country is None:
            await query.edit_message_text(escape(tr(language, "missing")))
            return
        data.pop("visa_search_mode", None)
        if mode == "p":
            data["visa_passport"] = country.code
            data.pop("visa_destination", None)
            data.pop("visa_residence", None)
            data["visa_purpose"] = "tourism"
            await query.edit_message_text(
                f"<b>{escape(tr(language, 'passport'))}:</b> "
                f"{escape(country_label(country.code, country.name, language))}"
                f" <code>{escape(country.code)}</code>\n"
                f"{escape(tr(language, 'choose_destination'))}",
                parse_mode="HTML",
                reply_markup=passport_keyboard(language),
            )
        elif mode == "d":
            if "visa_passport" not in data:
                await query.edit_message_text(
                    escape(tr(language, "choose_passport")),
                    reply_markup=home_keyboard(language),
                )
            else:
                data["visa_destination"] = country.code
                await _show_result(update, context, service, language, edit=True)
        else:
            data["visa_residence"] = country.code
            await _show_result(update, context, service, language, edit=True)
        return

    if action.startswith("visa:pur:"):
        purpose = action.partition("visa:pur:")[2]
        if purpose in {"tourism", "business", "transit"}:
            data["visa_purpose"] = purpose
        await _show_result(update, context, service, language, edit=True)
        return

    if action == "visa:result":
        await _show_result(update, context, service, language, edit=True)
        return

    if action == "visa:groups":
        if not data.get("visa_passport"):
            await query.edit_message_text(
                escape(tr(language, "choose_passport")),
                reply_markup=home_keyboard(language),
            )
        else:
            counts = await service.distribution(data["visa_passport"])
            await query.edit_message_text(
                f"<b>{escape(tr(language, 'list'))}</b>\n"
                f"<code>{escape(data['visa_passport'])}</code>",
                parse_mode="HTML",
                reply_markup=groups_keyboard(language, counts),
            )
        return

    if action.startswith("visa:list:"):
        parts = action.split(":")
        if len(parts) != 4 or not parts[3].isdigit() or not data.get("visa_passport"):
            await query.edit_message_text(escape(tr(language, "missing")))
            return
        group, page = parts[2], min(int(parts[3]), 500)
        try:
            rules, count = await service.listing(data["visa_passport"], group, page=page)
        except ValueError:
            await query.edit_message_text(escape(tr(language, "missing")))
            return
        lines = [
            f"<b>{escape(tr(language, group))}</b>",
            f"🛂 <code>{escape(data['visa_passport'])}</code> · "
            f"{escape(tr(language, 'more_results'))} {page + 1} · {count}",
            "",
        ]
        lines.extend(
            f"• {escape(country_label(rule.destination, rule.country_name, language))}"
            f" · {escape(status_label(rule.status, language))}"
            for rule in rules
        )
        if not rules:
            lines.append(escape(tr(language, "no_items")))
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=listing_keyboard(language, rules, group, page, count),
        )
        return

    if action.startswith("visa:section:") or action == "visa:rich":
        passport = data.get("visa_passport")
        destination = data.get("visa_destination")
        detail = await service.detail(passport, destination) if passport and destination else None
        if detail is None:
            await query.edit_message_text(
                escape(tr(language, "missing")),
                reply_markup=home_keyboard(language),
            )
            return
        if action == "visa:rich":
            rich = render_rich_report(detail, language)
            try:
                await send_rich_price_table(context.bot, query.message.chat_id, rich)
                await query.edit_message_text(
                    escape(tr(language, "more")) + "\n"
                    + escape(tr(language, "caution")),
                    reply_markup=detail_keyboard(language),
                )
            except Exception:
                LOGGER.warning("Visa rich transport unavailable, falling back", exc_info=True)
                await query.edit_message_text(
                    render_overview(detail, language),
                    parse_mode="HTML",
                    reply_markup=detail_keyboard(language),
                )
                # Standard HTML fallback, split into individual short sections.
                for section in ("types", "entry", "transit", "facts", "tips", "sources"):
                    await query.message.reply_text(
                        render_section(detail, language, section),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
            return
        section = action.rsplit(":", 1)[1]
        if section not in {"types", "entry", "transit", "facts", "tips", "faq", "sources"}:
            return
        await query.edit_message_text(
            render_section(detail, language, section),
            parse_mode="HTML",
            reply_markup=section_keyboard(language),
            disable_web_page_preview=True,
        )


async def visa_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: VisaCatalogService | None,
    language: str,
) -> None:
    if update.message is None:
        return
    if service is None or not await service.ready():
        await update.message.reply_text(tr(language, "empty"))
        return
    args = list(context.args or [])
    countries = await service.countries()
    if len(args) >= 2:
        passport, destination = args[0].upper(), args[1].upper()
        if _find_country(countries, passport) and _find_country(countries, destination):
            data = _context_data(context)
            data.update({
                "visa_passport": passport,
                "visa_destination": destination,
                "visa_purpose": "tourism",
            })
            if len(args) >= 3:
                residence = args[2].upper()
                data["visa_residence"] = residence if _find_country(countries, residence) else None
            else:
                data.pop("visa_residence", None)
            await _show_result(update, context, service, language, edit=False)
            return
        await update.message.reply_text(tr(language, "no_search"))
        return
    if len(args) == 1:
        selected = _find_country(countries, args[0])
        if selected:
            _context_data(context)["visa_passport"] = selected.code
            await update.message.reply_text(
                f"<b>{escape(tr(language, 'passport'))}: "
                f"{escape(country_label(selected.code, selected.name, language))}</b>",
                parse_mode="HTML",
                reply_markup=passport_keyboard(language),
            )
            return
    await open_visa_menu(update, context, service, language, edit=False)


async def visa_search_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: VisaCatalogService | None,
    language: str,
) -> bool:
    """Consume text only while the user explicitly has an active visa search."""
    data = _context_data(context)
    mode = data.get("visa_search_mode")
    if mode not in {"p", "d", "r"}:
        return False
    if update.message is None:
        return False
    if service is None or not await service.ready():
        await update.message.reply_text(tr(language, "empty"))
        data.pop("visa_search_mode", None)
        return True
    countries = await _country_catalog(service)
    matches = _matches(countries, update.message.text or "", language)
    if not matches:
        await update.message.reply_text(tr(language, "no_search"))
        return True
    data.pop("visa_search_mode", None)
    await update.message.reply_text(
        f"<b>{escape(tr(language, 'search_results'))}</b>",
        parse_mode="HTML",
        reply_markup=country_keyboard(matches, language, purpose=mode, query="searched"),
    )
    return True
