"""Regression coverage for Mini App buttons in group chats."""

from types import SimpleNamespace

import pytest

from flightiran.interfaces.telegram.handlers import TelegramDependencies, start_handler
from flightiran.interfaces.telegram.keyboards import main_menu

MINI_APP_URL = "https://example.org/flight-mini-app"


def _mini_app_button(markup):
    buttons = [
        button
        for row in markup.inline_keyboard
        for button in row
        if "مینی‌اپ" in button.text
    ]
    assert len(buttons) == 1
    return buttons[0]


@pytest.mark.parametrize("chat_type", ("group", "supergroup"))
def test_main_menu_uses_regular_url_in_group_chats(chat_type):
    # widgets_enabled is false for either group chat type.
    button = _mini_app_button(main_menu("fa", MINI_APP_URL, widgets_enabled=False))
    assert button.url == MINI_APP_URL
    assert button.web_app is None


def test_main_menu_keeps_native_web_app_in_private_chat():
    button = _mini_app_button(main_menu("fa", MINI_APP_URL, widgets_enabled=True))
    assert button.web_app.url == MINI_APP_URL
    assert button.url is None


def test_main_menu_does_not_advertise_invalid_web_app_urls():
    markup = main_menu("fa", "http://example.org/unsafe", widgets_enabled=True)
    assert all(
        "مینی‌اپ" not in button.text
        for row in markup.inline_keyboard
        for button in row
    )


class _Users:
    async def get_or_create_with_status(self, user_id, **kwargs):
        return SimpleNamespace(id=user_id), False

    async def get_language(self, user_id):
        return "fa"


class _Audit:
    async def record(self, *args, **kwargs):
        return None


class _Message:
    def __init__(self):
        self.sent = []

    async def reply_text(self, text, **kwargs):
        self.sent.append((text, kwargs))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("chat_type", "platform", "expected_web_app"),
    [
        ("group", "telegram", False),
        ("supergroup", "telegram", False),
        ("private", "telegram", True),
        ("private", "bale", False),
    ],
)
async def test_start_never_sends_unsupported_web_app_button(
    chat_type, platform, expected_web_app
):
    message = _Message()
    user = SimpleNamespace(id=42, username="traveler", first_name="Test", last_name=None)
    update = SimpleNamespace(
        effective_user=user,
        effective_chat=SimpleNamespace(type=chat_type, id=-100123 if chat_type != "private" else 42),
        message=message,
    )
    context = SimpleNamespace(
        bot=SimpleNamespace(platform=platform),
        user_data={},
        args=[],
    )
    deps = TelegramDependencies(
        users=_Users(), audit=_Audit(), web_app_url=MINI_APP_URL
    )

    await start_handler(update, context, deps)

    assert len(message.sent) == 1
    button = _mini_app_button(message.sent[0][1]["reply_markup"])
    if expected_web_app:
        assert button.web_app.url == MINI_APP_URL
        assert button.url is None
    else:
        assert button.web_app is None
        assert button.url == MINI_APP_URL
