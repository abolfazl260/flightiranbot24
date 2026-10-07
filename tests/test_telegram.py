from types import SimpleNamespace

import pytest

from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    callback_handler,
    language_handler,
    start_handler,
)


class MemoryUsers:
    def __init__(self):
        self.users = {}
        self.languages = {}

    async def get_or_create(self, telegram_id, **fields):
        self.users.setdefault(telegram_id, SimpleNamespace(id=telegram_id, **fields))
        return self.users[telegram_id]

    async def get_language(self, user_id):
        return self.languages.get(user_id, "en")

    async def set_language(self, user_id, language):
        self.languages[user_id] = language


class MemoryAudit:
    def __init__(self):
        self.events = []

    async def record(self, event_type, user_id=None, payload=None):
        self.events.append((event_type, user_id, payload))


class Message:
    def __init__(self):
        self.calls = []

    async def reply_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class Query(Message):
    data = "language:fa"

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def dependencies():
    return TelegramDependencies(MemoryUsers(), MemoryAudit())


def update(message=None, query=None):
    user = SimpleNamespace(id=42, username="user", first_name="Test", last_name=None)
    return SimpleNamespace(effective_user=user, message=message, callback_query=query)


@pytest.mark.asyncio
async def test_start_and_language_change_are_persistent():
    deps = dependencies()
    message = Message()
    await start_handler(update(message=message), None, deps)
    assert "Welcome" in message.calls[0][0][0]
    assert message.calls[0][1]["parse_mode"] == "HTML"

    language_message = Message()
    await language_handler(update(message=language_message), None, deps)
    assert "Choose your language" in language_message.calls[0][0][0]

    query = Query()
    await callback_handler(update(query=query), None, deps)
    assert deps.users.languages[42] == "fa"
    assert deps.audit.events[-1][0] == "language.changed"


@pytest.mark.asyncio
async def test_unknown_callback_has_safe_fallback():
    deps = dependencies()
    query = Query()
    query.data = "unexpected"
    await callback_handler(update(query=query), None, deps)
    assert "unavailable" in query.calls[0][0][0]
