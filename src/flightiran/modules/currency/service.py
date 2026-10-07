"""Currency quote orchestration and conversion."""

from __future__ import annotations

import asyncio
from typing import Iterable

from .domain import CurrencyQuote, QuoteStatus
from .provider import CurrencyProvider

DEFAULT_SYMBOLS = (
    "USD",
    "USDT",
    "EUR",
    "GBP",
    "AED",
    "CAD",
    "TRY",
    "SAR",
    "CNY",
    "AUD",
    "AFN",
    "COIN",
    "GOLD18",
    "BTC",
)


class CurrencyService:
    def __init__(
        self, provider: CurrencyProvider, symbols: Iterable[str] = DEFAULT_SYMBOLS
    ) -> None:
        self.provider = provider
        self.symbols = tuple(symbols)

    async def quotes(self) -> list[CurrencyQuote]:
        async def one(symbol: str) -> CurrencyQuote:
            try:
                return await self.provider.fetch(symbol)
            except Exception:
                try:
                    return await self.provider.fetch(symbol, use_proxy=True)
                except Exception:
                    return CurrencyQuote(symbol, symbol, None, status=QuoteStatus.UNAVAILABLE)

        return list(await asyncio.gather(*(one(symbol) for symbol in self.symbols)))


def convert_amount(amount: float, source: CurrencyQuote, target: CurrencyQuote) -> float | None:
    if source.price is None or target.price is None or source.price <= 0:
        return None
    return amount * source.price / target.price
