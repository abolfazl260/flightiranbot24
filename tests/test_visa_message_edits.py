"""Regression tests for duplicate Telegram visa callback edits."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

from flightiran.interfaces.telegram.visa_flow import (
    _edit_message_text,
    handle_visa_callback,
    open_visa_menu,
)


@pytest.mark.asyncio
async def test_edit_message_text_ignores_unchanged_content():
    query = SimpleNamespace(
        data="visa:result",
        edit_message_text=AsyncMock(
            side_effect=BadRequest(
                "Message is not modified: specified new message content and "
                "reply markup are exactly the same"
            )
        ),
    )

    await _edit_message_text(query, "<b>Visa</b>", parse_mode="HTML")

    query.edit_message_text.assert_awaited_once_with(
        "<b>Visa</b>", parse_mode="HTML"
    )


@pytest.mark.asyncio
async def test_edit_message_text_preserves_other_telegram_errors():
    query = SimpleNamespace(
        data="visa:result",
        edit_message_text=AsyncMock(
            side_effect=BadRequest("Message to edit not found")
        ),
    )

    with pytest.raises(BadRequest, match="Message to edit not found"):
        await _edit_message_text(query, "Visa")


@pytest.mark.asyncio
async def test_repeated_visa_result_callback_does_not_raise():
    query = SimpleNamespace(
        data="visa:result",
        edit_message_text=AsyncMock(
            side_effect=BadRequest("Message is not modified")
        ),
    )
    context = SimpleNamespace(user_data={})
    service = SimpleNamespace(ready=AsyncMock(return_value=True))

    await handle_visa_callback(
        SimpleNamespace(callback_query=query), context, service, "fa"
    )

    assert context.user_data["visa_passport"] == "IR"
    query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_visa_home_callback_does_not_raise():
    query = SimpleNamespace(
        data="visa:home",
        edit_message_text=AsyncMock(
            side_effect=BadRequest("Message is not modified")
        ),
    )
    context = SimpleNamespace(user_data={})
    service = SimpleNamespace(
        ready=AsyncMock(return_value=True),
        countries=AsyncMock(return_value=[]),
    )

    await open_visa_menu(
        SimpleNamespace(callback_query=query), context, service, "fa"
    )

    query.edit_message_text.assert_awaited_once()
