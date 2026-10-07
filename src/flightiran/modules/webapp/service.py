"""Server-side Telegram Web App init-data validation."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qsl


class WebAppAuthenticator:
    def __init__(self, bot_token: str, max_age_seconds: int = 86400) -> None:
        self._secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        self.max_age_seconds = max_age_seconds

    def validate(self, init_data: str) -> dict[str, str]:
        values = dict(parse_qsl(init_data, keep_blank_values=True))
        provided = values.pop("hash", None)
        if not provided:
            raise ValueError("missing init data hash")
        auth_date = int(values.get("auth_date", "0"))
        if auth_date <= 0 or time.time() - auth_date > self.max_age_seconds:
            raise ValueError("expired init data")
        data_check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
        expected = hmac.new(self._secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, provided):
            raise ValueError("invalid init data")
        return values


class WebAppService:
    def __init__(self, authenticator: WebAppAuthenticator, enabled: bool = False) -> None:
        self.authenticator = authenticator
        self.enabled = enabled

    def session(self, init_data: str) -> dict[str, str]:
        if not self.enabled:
            raise RuntimeError("web app disabled")
        return self.authenticator.validate(init_data)

    def fallback(self) -> str:
        return "Use the Telegram menu for this feature."
