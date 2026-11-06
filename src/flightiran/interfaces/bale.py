"""Bale Bot API transport for the existing python-telegram-bot handlers.

Bale documents a Telegram-compatible HTTP API with a different endpoint and
Markdown (rather than Telegram HTML) text formatting. Keep the application
handlers unchanged and adapt only the outgoing transport.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from telegram.ext import ExtBot

BALE_API_URL = "https://tapi.bale.ai/bot"
BALE_FILE_URL = "https://tapi.bale.ai/file/bot"


class _PlainTextFromHTML(HTMLParser):
    """Make Telegram HTML messages legible in Bale without leaking HTML tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[tuple[str | None, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.links.append((dict(attrs).get("href"), len(self.parts)))
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"p", "div", "tr", "li"} and self.parts:
            self.parts.append("\n")
        elif tag in {"td", "th"} and self.parts:
            self.parts.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.links:
            href, start = self.links.pop()
            label = "".join(self.parts[start:]).strip()
            if href and href != label and href.startswith(("https://", "http://")):
                self.parts.append(f" ({href})")
        elif tag in {"p", "div", "tr", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def telegram_html_to_bale_text(value: str) -> str:
    """Return predictable plain text (and preserve hyperlinks) for Bale.

    Bale's documented message formatting is Markdown, not Telegram's HTML;
    avoiding parse_mode entirely is safest for text containing prices, symbols
    or user-provided content.
    """

    parser = _PlainTextFromHTML()
    parser.feed(value)
    parser.close()
    return re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()


class BaleBot(ExtBot):
    """Use the official Bale endpoint without forking Telegram handlers."""

    platform = "bale"

    def __init__(self, token: str) -> None:
        super().__init__(
            token=token,
            base_url=BALE_API_URL,
            base_file_url=BALE_FILE_URL,
        )

    async def _post(self, endpoint: str, data: dict | None = None, **kwargs):
        if endpoint.lower() == "answercallbackquery" and str(
            (data or {}).get("callback_query_id", "")
        ).startswith("1"):
            # Older Bale clients cannot display callback answers.
            return True

        if data is not None:
            data = dict(data)
            if endpoint.lower() in {
                "sendmessage", "editmessagetext", "editmessagecaption",
                "sendphoto", "senddocument", "sendvideo", "sendaudio",
            } and str(data.get("parse_mode", "")).upper() == "HTML":
                field = "caption" if endpoint.lower() == "editmessagecaption" else (
                    "text" if endpoint.lower() in {"sendmessage", "editmessagetext"} else "caption"
                )
                if isinstance(data.get(field), str):
                    data[field] = telegram_html_to_bale_text(data[field])
                data.pop("parse_mode", None)
            # These newer Telegram options are not part of Bale's documented API.
            data.pop("link_preview_options", None)
            data.pop("disable_web_page_preview", None)

        return await super()._post(endpoint, data, **kwargs)
