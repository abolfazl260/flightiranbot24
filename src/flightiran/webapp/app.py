"""FastAPI Web App shell with Telegram init-data authentication."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from flightiran.config import Settings, load_settings
from flightiran.db.engine import Database, create_database
from flightiran.db.repositories import SQLiteMz724PriceHistoryRepository, SQLiteUserRepository
from flightiran.modules.webapp import WebAppAuthenticator, WebAppService
from flightiran.webapp.mini_api import mini_router
from flightiran.webapp.ticket_prices import PublicTicketPriceFeed

STATIC_DIR = Path(__file__).with_name("static")
LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None, *, activity_database: Database | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    service = WebAppService(
        WebAppAuthenticator(settings.telegram_bot_token.get_secret_value()),
        enabled=settings.web_app_enabled,
    )
    public_prices = (
        PublicTicketPriceFeed(SQLiteMz724PriceHistoryRepository(activity_database))
        if activity_database is not None else None
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            if activity_database is not None:
                await activity_database.close()

    app = FastAPI(
        title="Flight Iran Bot Web App", docs_url=None, redoc_url=None, lifespan=lifespan
    )
    users = SQLiteUserRepository(activity_database) if activity_database else None
    app.include_router(mini_router(settings, activity_database, public_prices))
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="mini-assets")

    @app.middleware("http")
    async def mini_security_headers(request, call_next):
        response = await call_next(request)
        if request.url.path in ("/", "/mini", "/mini/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self' https://telegram.org; "
                "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
                "base-uri 'none'; object-src 'none'; form-action 'none'"
            )
            response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/mini/") or request.url.path in (
            "/api/session", "/api/dashboard"
        ):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    async def record_web_activity(user: dict) -> None:
        if users is None:
            return
        raw_id = user.get("id")
        if type(raw_id) is not int or raw_id <= 0:
            return
        fields = {
            key: value if isinstance(value, str) else None
            for key, value in (
                ("username", user.get("username")),
                ("first_name", user.get("first_name")),
                ("last_name", user.get("last_name")),
            )
        }
        try:
            await users.mark_active(raw_id, **fields)
        except Exception:
            LOGGER.exception("authenticated_web_activity_tracking_failed")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    @app.get("/mini", response_class=HTMLResponse)
    @app.get("/mini/", response_class=HTMLResponse)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html; charset=utf-8")

    def authenticate(init_data: str | None) -> dict[str, str]:
        if not init_data:
            raise HTTPException(status_code=401, detail="Telegram init data is required")
        try:
            return service.session(init_data)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="Invalid Telegram session") from exc

    @app.get("/api/v1/tickets/prices")
    async def public_ticket_prices(response: Response) -> dict[str, object]:
        """No Telegram login required: public quotes from the shared database."""
        response.headers["Cache-Control"] = "public, max-age=60"
        if public_prices is None:
            raise HTTPException(status_code=503, detail="Ticket database unavailable")
        try:
            return await public_prices.get()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Ticket prices unavailable") from exc

    @app.get("/api/session")
    async def session(x_telegram_init_data: str | None = Header(default=None)) -> dict[str, object]:
        values = authenticate(x_telegram_init_data)
        user = json.loads(values["user"]) if values.get("user") else {}
        await record_web_activity(user)
        return {"user": {"id": user.get("id"), "first_name": user.get("first_name")}}

    @app.get("/api/dashboard")
    async def dashboard(
        x_telegram_init_data: str | None = Header(default=None),
    ) -> dict[str, object]:
        values = authenticate(x_telegram_init_data)
        user = json.loads(values.get("user", "{}"))
        await record_web_activity(user)
        return {
            "user_id": user.get("id"),
            "features": ["airport", "tickets", "visa", "alerts"],
        }

    return app


def main() -> None:
    import uvicorn

    settings = load_settings()
    settings.validate_for_production()
    database = create_database(settings.database_url)
    uvicorn.run(
        create_app(settings, activity_database=database), host="0.0.0.0", port=8000
    )
