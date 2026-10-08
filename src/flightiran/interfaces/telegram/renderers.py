"""Safe HTML renderers for Telegram messages."""

from html import escape

from .localization import normalize_language, safe_text, text


def render_main_menu(language: str, first_name: str | None = None) -> str:
    language = normalize_language(language)
    name = (first_name or "").strip()[:80]
    greeting = escape(text(language, "welcome_greeting").format(name=name)).strip()
    lines = [
        greeting,
        f"<b>{safe_text(language, 'welcome_title')}</b>",
        "",
        safe_text(language, "welcome_intro"),
        safe_text(language, "welcome_description"),
        "",
        f"<b>{safe_text(language, 'welcome_services')}</b>",
    ]
    lines.extend(escape(item) for item in text(language, "welcome_items"))
    lines.extend(["", safe_text(language, "welcome_choose")])
    return "\n".join(lines)


def render_help(language: str) -> str:
    language = normalize_language(language)
    lines = [
        f"<b>{safe_text(language, 'help_title')}</b>",
        safe_text(language, "help_intro"),
        "",
        f"<b>{safe_text(language, 'help_commands')}</b>",
    ]
    for command, key in (
        ("/start", "help_start"),
        ("/help", "help_help"),
        ("/language", "help_language"),
        ("/flight", "help_flight"),
        ("/price", "help_price"),
    ):
        lines.append(f"<code>{command}</code> — {safe_text(language, key)}")
    lines.extend([
        "",
        f"<b>{safe_text(language, 'help_menu')}</b>",
        safe_text(language, "help_menu_body"),
        "",
        safe_text(language, "help_note"),
        "",
        safe_text(language, "help_back"),
    ])
    return "\n".join(lines)


def render_language_prompt(language: str) -> str:
    return f"<b>{safe_text(language, 'language_prompt')}</b>"
