"""Reusable async HTTP client with provider-safe resilience policies."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

from .cache import TTLCache
from .errors import (
    ProviderHTTPError,
    ProviderInvalidResponse,
    ProviderRateLimited,
    ProviderTimeout,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderHttpConfig:
    timeout_seconds: float = 10.0
    max_retries: int = 2
    backoff_seconds: float = 0.25
    cache_ttl_seconds: float = 0.0
    default_headers: dict[str, str] = field(default_factory=dict)


class ProviderHttpClient:
    def __init__(
        self,
        config: ProviderHttpConfig | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or ProviderHttpConfig()
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers=self.config.default_headers,
            transport=transport,
        )
        self._owns_client = client is None
        self._cache: TTLCache[dict[str, Any]] | None = (
            TTLCache(self.config.cache_ttl_seconds) if self.config.cache_ttl_seconds > 0 else None
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "ProviderHttpClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def get_json(
        self,
        url: str,
        *,
        provider: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        if cache_key and self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        response = await self._request(
            "GET", url, provider=provider, params=params, headers=headers
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderInvalidResponse(f"Provider {provider} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ProviderInvalidResponse(f"Provider {provider} returned an unexpected payload")
        if cache_key and self._cache:
            self._cache.set(cache_key, payload)
        return payload

    async def _request(
        self, method: str, url: str, *, provider: str, **kwargs: Any
    ) -> httpx.Response:
        safe_url = urlsplit(url)
        LOGGER.debug(
            "provider_request provider=%s method=%s path=%s", provider, method, safe_url.path
        )
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                if attempt >= self.config.max_retries:
                    raise ProviderTimeout(f"Provider {provider} timed out") from exc
                await asyncio.sleep(self.config.backoff_seconds * (2**attempt))
                continue
            if response.status_code == 429:
                if attempt >= self.config.max_retries:
                    raise ProviderRateLimited(429, provider)
                await asyncio.sleep(self.config.backoff_seconds * (2**attempt))
                continue
            if response.status_code >= 500:
                if attempt >= self.config.max_retries:
                    raise ProviderHTTPError(response.status_code, provider)
                await asyncio.sleep(self.config.backoff_seconds * (2**attempt))
                continue
            if response.status_code >= 400:
                raise ProviderHTTPError(response.status_code, provider)
            return response
        raise ProviderTimeout(f"Provider {provider} timed out")
