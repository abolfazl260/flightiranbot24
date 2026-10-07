"""Provider contract and payload normalization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from flightiran.infrastructure.http import ProviderClient

from .domain import CurrencyQuote, QuoteStatus


class CurrencyProvider(Protocol):
    async def fetch(self, symbol: str, *, use_proxy: bool = False) -> CurrencyQuote: ...


class HttpCurrencyProvider:
    def __init__(
        self, client: ProviderClient, endpoint: str, source_url: str | None = None
    ) -> None:
        self.client = client
        self.endpoint = endpoint
        self.source_url = source_url or endpoint

    async def fetch(self, symbol: str, *, use_proxy: bool = False) -> CurrencyQuote:
        payload = await self.client.get_json(
            self.endpoint,
            provider="currency",
            params={"symbol": symbol, "proxy": str(use_proxy).lower()},
            cache_key=f"currency:{symbol}:{use_proxy}",
        )
        return self.parse(symbol, payload, self.source_url)

    @staticmethod
    def parse(symbol: str, payload: dict[str, Any], source_url: str | None = None) -> CurrencyQuote:
        value = payload.get("price")
        change = payload.get("change_percent")
        try:
            price = float(value) if value is not None else None
            change_value = float(change) if change is not None else None
        except (TypeError, ValueError):
            price, change_value = None, None
        direction = (
            "up" if (change_value or 0) > 0 else "down" if (change_value or 0) < 0 else "flat"
        )
        timestamp = payload.get("updated_at")
        updated_at = (
            datetime.fromtimestamp(timestamp, timezone.utc)
            if isinstance(timestamp, (int, float))
            else None
        )
        return CurrencyQuote(
            symbol=symbol,
            label=str(payload.get("label", symbol)),
            price=price,
            change_percent=change_value,
            direction=direction,
            updated_at=updated_at,
            source_url=source_url,
            status=QuoteStatus.FRESH if price is not None else QuoteStatus.UNAVAILABLE,
        )
