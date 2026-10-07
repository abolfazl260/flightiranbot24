import pytest

from flightiran.modules.currency import CurrencyQuote, CurrencyService, QuoteStatus, convert_amount
from flightiran.modules.currency.provider import HttpCurrencyProvider


def test_parsing_and_conversion():
    quote = HttpCurrencyProvider.parse(
        "USD", {"price": "100", "change_percent": -2, "updated_at": 0}
    )
    assert quote.price == 100
    assert quote.direction == "down"
    assert quote.updated_at.year == 1970
    assert convert_amount(3, quote, CurrencyQuote("EUR", "EUR", 150)) == 2
    unavailable = HttpCurrencyProvider.parse("BAD", {"price": "invalid"})
    assert unavailable.status == QuoteStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_provider_failure_has_fallback_and_does_not_hide_other_values():
    class Provider:
        async def fetch(self, symbol, use_proxy=False):
            if symbol == "USD" and not use_proxy:
                raise RuntimeError("direct failed")
            if symbol == "BAD":
                raise RuntimeError("not available")
            return CurrencyQuote(symbol, symbol, 100)

    quotes = await CurrencyService(Provider(), ["USD", "EUR", "BAD"]).quotes()
    assert [quote.price for quote in quotes] == [100, 100, None]
    assert quotes[2].status == QuoteStatus.UNAVAILABLE
