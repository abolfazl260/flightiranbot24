"""FastAPI Web App shell with Telegram init-data authentication."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from flightiran.config import Settings, load_settings
from flightiran.modules.webapp import WebAppAuthenticator, WebAppService

STATIC_DIR = Path(__file__).with_name("static")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    service = WebAppService(
        WebAppAuthenticator(settings.telegram_bot_token.get_secret_value()),
        enabled=settings.web_app_enabled,
    )
    app = FastAPI(title="Flight Iran Bot Web App", docs_url=None, redoc_url=None)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))

    def authenticate(init_data: str | None) -> dict[str, str]:
        if not init_data:
            raise HTTPException(status_code=401, detail="Telegram init data is required")
        try:
            return service.session(init_data)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="Invalid Telegram session") from exc

    @app.get("/api/session")
    async def session(x_telegram_init_data: str | None = Header(default=None)) -> dict[str, object]:
        values = authenticate(x_telegram_init_data)
        user = json.loads(values["user"]) if values.get("user") else {}
        return {"user": {"id": user.get("id"), "first_name": user.get("first_name")}}

    @app.get("/api/dashboard")
    async def dashboard(
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        values = authenticate(x_telegram_init_data)
        return {
            "user_id": json.loads(values.get("user", "{}")).get("id"),
            "features": ["airport", "tickets", "visa", "alerts"],
        }

    return app


def main() -> None:
    import uvicorn

    settings = load_settings()
    settings.validate_for_production()
    uvicorn.run(create_app(settings), host="0.0.0.0", port=8000)
