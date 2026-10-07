import httpx
import pytest
from pydantic import BaseModel

from flightiran.infrastructure.http import (
    ProviderHttpClient,
    ProviderHttpConfig,
    ProviderHTTPError,
    ProviderInvalidResponse,
    ProviderRateLimited,
    ProviderTimeout,
    RateLimiter,
    validate_dto,
)


class Payload(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_success_is_json_and_cacheable():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"value": 3})

    client = ProviderHttpClient(
        ProviderHttpConfig(cache_ttl_seconds=30), transport=httpx.MockTransport(handler)
    )
    assert await client.get_json("https://example.test/data", provider="test", cache_key="x") == {
        "value": 3
    }
    assert await client.get_json("https://example.test/data", provider="test", cache_key="x") == {
        "value": 3
    }
    assert calls == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_timeout_retries_then_raises():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow")

    client = ProviderHttpClient(
        ProviderHttpConfig(max_retries=2, backoff_seconds=0), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderTimeout):
        await client.get_json("https://example.test/data", provider="test")
    assert calls == 3
    await client.aclose()


@pytest.mark.asyncio
async def test_status_handling_and_invalid_json():
    async def four_oh_four(request):
        return httpx.Response(404)

    client = ProviderHttpClient(
        ProviderHttpConfig(backoff_seconds=0), transport=httpx.MockTransport(four_oh_four)
    )
    with pytest.raises(ProviderHTTPError) as error:
        await client.get_json("https://example.test/data", provider="test")
    assert error.value.status_code == 404
    await client.aclose()

    async def bad_json(request):
        return httpx.Response(200, text="not json")

    client = ProviderHttpClient(transport=httpx.MockTransport(bad_json))
    with pytest.raises(ProviderInvalidResponse):
        await client.get_json("https://example.test/data", provider="test")
    await client.aclose()


@pytest.mark.asyncio
async def test_server_error_and_rate_limit_stop_at_limit():
    async def server_error(request):
        return httpx.Response(503)

    client = ProviderHttpClient(
        ProviderHttpConfig(max_retries=1, backoff_seconds=0),
        transport=httpx.MockTransport(server_error),
    )
    with pytest.raises(ProviderHTTPError):
        await client.get_json("https://example.test/data", provider="test")
    await client.aclose()

    async def rate_limit(request):
        return httpx.Response(429)

    client = ProviderHttpClient(
        ProviderHttpConfig(max_retries=1, backoff_seconds=0),
        transport=httpx.MockTransport(rate_limit),
    )
    with pytest.raises(ProviderRateLimited):
        await client.get_json("https://example.test/data", provider="test")
    await client.aclose()


@pytest.mark.asyncio
async def test_limiter_and_dto_validation():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert await limiter.acquire("user:1")
    assert not await limiter.acquire("user:1")
    assert validate_dto(Payload, {"value": 4}, "test").value == 4
    with pytest.raises(ProviderInvalidResponse):
        validate_dto(Payload, {"value": "bad"}, "test")
