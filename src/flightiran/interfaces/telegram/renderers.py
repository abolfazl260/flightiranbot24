"""Safe HTML renderers for Telegram messages."""

from .localization import safe_text


def render_main_menu(language: str) -> str:
    return f"<b>{safe_text(language, 'welcome')}</b>\n\n{safe_text(language, 'menu')}"


def render_language_prompt(language: str) -> str:
    return f"<b>{safe_text(language, 'language_prompt')}</b>"
