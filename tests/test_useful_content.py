import pytest

from flightiran.interfaces.telegram.handlers import TelegramDependencies, callback_handler
from flightiran.interfaces.telegram.useful_content import useful_category_menu, useful_menu
from flightiran.modules.useful_content import UsefulContentCatalog, UsefulLink


def test_catalog_rejects_duplicate_ids_and_invalid_urls():
    with pytest.raises(ValueError):
        UsefulContentCatalog(
            [
                UsefulLink("same", "A", "https://example.com/a"),
                UsefulLink("same", "B", "https://example.com/b"),
            ]
        )
    with pytest.raises(ValueError):
        UsefulLink("bad", "Bad", "javascript:alert(1)")


def test_useful_menu_has_general_links_and_categories():
    catalog = UsefulContentCatalog(
        [
            UsefulLink("a", "A", "https://example.com/a"),
            UsefulLink("b", "B", "https://example.com/b", "flight-rules"),
        ]
    )
    keyboard = useful_menu("fa", catalog)
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert any(button.callback_data == "useful:flights" for button in buttons)
    assert any(button.callback_data == "useful:baggage" for button in buttons)
    assert not any(button.url for button in buttons)
    assert all(button.url or button.callback_data for button in buttons)


class _Users:
    async def get_or_create(self, telegram_id, **fields):
        from types import SimpleNamespace

        return SimpleNamespace(id=telegram_id)

    async def get_language(self, user_id):
        return "fa"


class _Audit:
    def __init__(self):
        self.events = []

    async def record(self, *args, **kwargs):
        self.events.append((args, kwargs))


class _Query:
    def __init__(self, data):
        self.data = data
        self.calls = []

    async def answer(self):
        pass

    async def edit_message_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


@pytest.mark.asyncio
async def test_useful_category_callback_renders_and_audits():
    from types import SimpleNamespace

    audit = _Audit()
    deps = TelegramDependencies(
        _Users(),
        audit,
        useful_catalog=UsefulContentCatalog(
            [UsefulLink("a", "A", "https://example.com/a", "flight-rules")]
        ),
    )
    query = _Query("useful:flight-rules")
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42, username="u", first_name="U", last_name=None),
        message=None,
        callback_query=query,
    )
    await callback_handler(update, None, deps)
    assert "قوانین پرواز" in query.calls[0][0][0]
    assert audit.events[-1][0][0] == "useful.category.viewed"


def test_default_catalog_groups_every_resource():
    from flightiran.modules.useful_content.catalog import default_catalog

    catalog = default_catalog()
    expected = {
        "documents", "flights", "baggage", "payments", "tips",
        "flight-rules", "travel-sites",
    }
    assert {link.category for link in catalog.all()} == expected
    assert len(catalog.all()) == 21
    for category in expected:
        assert catalog.by_category(category)


def test_navigation_to_country_resources_and_back():
    from flightiran.modules.useful_content.catalog import default_catalog

    catalog = default_catalog()
    baggage = useful_category_menu("fa", catalog, "baggage")
    assert any(
        button.callback_data == "useful:flight-rules"
        for row in baggage.inline_keyboard for button in row
    )
    flight_rules = useful_category_menu("fa", catalog, "flight-rules")
    assert flight_rules.inline_keyboard[-1][0].callback_data == "useful:baggage"
    countries = useful_category_menu("fa", catalog, "travel-sites")
    assert countries.inline_keyboard[-1][0].callback_data == "useful:international"
