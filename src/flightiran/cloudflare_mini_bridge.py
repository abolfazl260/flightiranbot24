"""Outbound-only bridge from the workers.dev Mini App to the authoritative SQLite bot.

Cloudflare verifies the *real* signed Telegram initData before queuing a job.
Only this server can fetch those jobs with the private PUBLISH_TOKEN. A short-
lived, locally signed initData assertion lets us reuse the existing FastAPI
mini endpoints and their user-scoped domain services without any inbound
HTTP/TLS on the server. Real Telegram tokens are never logged or sent to D1.

A mutating job is never re-leased automatically after timeout. This avoids
accidental duplicate alert creation if SQLite committed before an ack was lost.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from collections.abc import Mapping
from urllib.parse import urlencode

import httpx

from flightiran.cloudflare_publish import validate_origin
from flightiran.config import load_settings
from flightiran.db.engine import create_database
from flightiran.webapp.app import create_app

LOGGER = logging.getLogger(__name__)
OPERATIONS: dict[str, tuple[str, str]] = {
    "bootstrap": ("GET", "/api/mini/bootstrap"),
    "useful": ("GET", "/api/mini/useful"),
    "alerts": ("GET", "/api/mini/alerts"),
    "passport": ("POST", "/api/mini/passport"),
    "price_create": ("POST", "/api/mini/alerts/prices"),
    "price_status": ("PATCH", "/api/mini/alerts/prices/{id}"),
    "price_delete": ("DELETE", "/api/mini/alerts/prices/{id}"),
    "visa_create": ("POST", "/api/mini/alerts/visa"),
    "visa_status": ("PATCH", "/api/mini/alerts/visa/{id}"),
    "visa_delete": ("DELETE", "/api/mini/alerts/visa/{id}"),
}


def signed_local_init_data(bot_token: str, job: Mapping) -> str:
    """Internal attestation: the remote Worker already validated Telegram HMAC.

    This HMAC is used only inside an in-memory ASGITransport and is NEVER
    transmitted to the Worker, written to D1, or returned to a browser.
    """
    telegram_id = job.get("telegram_id")
    if type(telegram_id) is not int or not 0 < telegram_id < 2**53:
        raise ValueError("invalid Telegram user identifier")
    profile = job.get("user")
    if not isinstance(profile, dict):
        raise ValueError("missing validated Telegram profile")
    user = {"id": telegram_id}
    for key in ("first_name", "last_name", "username"):
        value = profile.get(key)
        if value is not None:
            if not isinstance(value, str) or len(value) > 100:
                raise ValueError("invalid Telegram profile field")
            user[key] = value
    values = {
        "auth_date": str(int(time.time())),
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def job_destination(job: Mapping) -> tuple[str, str, dict | None]:
    operation = job.get("operation")
    if operation not in OPERATIONS:
        raise ValueError("invalid Mini App operation")
    method, path = OPERATIONS[operation]
    payload = job.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("invalid Mini App payload")
    if "{id}" in path:
        identifier = payload.get("id")
        if type(identifier) is not int or not 0 < identifier < 10**13:
            raise ValueError("invalid Mini App alert identifier")
        path = path.replace("{id}", str(identifier))
    if method in {"POST", "PATCH"}:
        body = {key: value for key, value in payload.items() if key != "id"}
    else:
        body = None
    return method, path, body


class MiniAppBridge:
    """Process private Mini App jobs through the existing authenticated app."""

    def __init__(
        self,
        origin: str,
        publish_token: str,
        bot_token: str,
        local_client: httpx.AsyncClient,
        remote_client: httpx.AsyncClient,
    ) -> None:
        self.origin = validate_origin(origin)
        if len(publish_token) < 32 or len(bot_token) < 20:
            raise ValueError("private Worker publishing and Telegram bot tokens are required")
        self._publish_token = publish_token
        self._bot_token = bot_token
        self._local = local_client
        self._remote = remote_client

    def _headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self._publish_token, "Accept": "application/json"}

    async def execute(self, job: Mapping) -> tuple[int, dict]:
        try:
            method, path, body = job_destination(job)
            signed = signed_local_init_data(self._bot_token, job)
            response = await self._local.request(
                method, path,
                headers={"X-Telegram-Init-Data": signed},
                json=body if method in {"POST", "PATCH"} else None,
            )
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Unexpected Mini App API response")
            if response.status_code not in (200, 201, 400, 401, 404, 409, 422, 429, 503):
                raise ValueError("Unexpected Mini App API status")
            return response.status_code, payload
        except ValueError:
            LOGGER.warning("cloudflare_mini_rejected_invalid_job")
            return 422, {"error": "Invalid Mini App request"}
        except Exception:
            LOGGER.exception("cloudflare_mini_local_execution_failed")
            return 503, {"error": "Mini App action temporarily unavailable"}

    async def sync_once(self) -> int:
        response = await self._remote.get(
            self.origin + "internal/v1/mini/jobs", headers=self._headers()
        )
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
        if not isinstance(jobs, list) or len(jobs) > 8:
            raise ValueError("Invalid Mini App job batch")
        completed = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_id = job.get("id")
            if not isinstance(job_id, str) or len(job_id) != 36 or not all(
                ch in "0123456789abcdef-" for ch in job_id.lower()
            ):
                LOGGER.warning("cloudflare_mini_invalid_job_id")
                continue
            status, payload = await self.execute(job)
            try:
                acknowledgement = await self._remote.post(
                    self.origin + f"internal/v1/mini/jobs/{job_id}/result",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={"http_status": status, "body": payload},
                )
                acknowledgement.raise_for_status()
                if acknowledgement.json().get("accepted") is not True:
                    raise ValueError("Worker did not acknowledge Mini App result")
            except (httpx.HTTPError, ValueError):
                # Mutations are deliberately not re-executed after a lease expires.
                LOGGER.exception(
                    "cloudflare_mini_ack_failed job=%s operation=%s",
                    job_id, job.get("operation"),
                )
                continue
            completed += 1
            LOGGER.info("cloudflare_mini_completed operation=%s http=%s", job.get("operation"), status)
        return completed


async def run(*, once: bool, interval_seconds: int) -> int:
    origin = os.environ.get("CLOUDFLARE_PUBLIC_API_ORIGIN", "")
    token = os.environ.get("CLOUDFLARE_PUBLISH_TOKEN", "")
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    settings = load_settings()
    database = create_database(database_url)
    try:
        # WEB_APP_URL is no longer needed by this bridge. The in-memory ASGI
        # handler runs with the feature flag enabled; the public Worker still
        # validates Telegram initData separately before any job is accepted.
        local_settings = settings.model_copy(update={"web_app_enabled": True})
        web_app = create_app(local_settings, activity_database=database)
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=web_app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as local,
            httpx.AsyncClient(
                follow_redirects=False, timeout=httpx.Timeout(30),
            ) as remote,
        ):
            bridge = MiniAppBridge(
                origin, token, settings.telegram_bot_token.get_secret_value(),
                local, remote,
            )
            while True:
                try:
                    completed = await bridge.sync_once()
                    if completed:
                        LOGGER.info("cloudflare_mini_batch_completed count=%s", completed)
                except Exception:
                    LOGGER.exception("cloudflare_mini_poll_failed")
                    if once:
                        return 1
                if once:
                    return 0
                await asyncio.sleep(interval_seconds)
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve signed Mini App requests via D1 queue")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=5)
    args = parser.parse_args()
    if not 2 <= args.interval_seconds <= 60:
        parser.error("interval must be between 2 and 60 seconds")
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(run(once=args.once, interval_seconds=args.interval_seconds)))


if __name__ == "__main__":
    main()
