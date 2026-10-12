"""Authenticated, user-scoped JSON API for the Persian Telegram Mini App.

This router uses the bot's existing SQLite database and domain services. All
mutations require Telegram's signed initData; no browser-supplied user ID is
trusted. The public Android ticket API remains unchanged.
"""

import json
import re
from dataclasses import asdict
from typing import Annotated, Literal

from babel import Locale
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from flightiran.config import Settings
from flightiran.db.engine import Database
from flightiran.db.models import User
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.support import support_url
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.useful_content import default_catalog
from flightiran.modules.visa.catalog import VisaCatalogService
from flightiran.modules.visa.watch import VisaWatchService
from flightiran.modules.webapp import WebAppAuthenticator, WebAppService
from flightiran.webapp.ticket_prices import PublicTicketPriceFeed

_CODE = re.compile(r"[A-Z]{2}\Z")
_FA_TERRITORIES = Locale.parse("fa").territories


def persian_country(code: str, fallback: str) -> str:
    return str(_FA_TERRITORIES.get(code) or fallback)


_CATEGORIES = (
    ("documents", "مدارک و خروج از کشور"),
    ("flights", "پرواز و حقوق مسافر"),
    ("baggage", "بار و گمرک"),
    ("international", "سفر خارجی"),
    ("payments", "هزینه و بیمه"),
    ("tips", "نکات سفر"),
    ("flight-rules", "قوانین بار و پرواز"),
    ("travel-sites", "منابع سفر کشورها"),
)


class PassportSelection(BaseModel):
    passport: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")


class PriceAlertCreation(BaseModel):
    origin: str = Field(min_length=1, max_length=128)
    destination: str = Field(min_length=1, max_length=128)
    kind: Literal["percent", "price"]
    threshold_percent: int | None = Field(default=None, ge=5, le=50)
    target_price_toman: int | None = Field(default=None, gt=0, le=1_000_000_000_000)


class PriceAlertStatus(BaseModel):
    status: Literal["active", "paused"]


class VisaWatchCreation(BaseModel):
    passport: str = Field(pattern=r"^[A-Z]{2}$")
    destination: str = Field(pattern=r"^[A-Z]{2}$")


class VisaWatchStatus(BaseModel):
    active: bool


def mini_router(
    settings: Settings, database: Database | None, public_prices: PublicTicketPriceFeed | None,
) -> APIRouter:
    router = APIRouter(prefix="/api/mini")
    authenticator = WebAppService(
        WebAppAuthenticator(settings.telegram_bot_token.get_secret_value()),
        enabled=settings.web_app_enabled,
    )
    users = SQLiteUserRepository(database) if database else None
    visas = VisaCatalogService(database) if database else None
    prices = PriceAlertService(database) if database else None
    watches = VisaWatchService(database) if database else None

    async def current_user(
        x_telegram_init_data: Annotated[str | None, Header()] = None,
    ) -> User:
        if not x_telegram_init_data:
            raise HTTPException(401, "Telegram init data is required")
        try:
            values = authenticator.session(x_telegram_init_data)
            user = json.loads(values.get("user", "null"))
        except (RuntimeError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(401, "Invalid Telegram session") from exc
        if not isinstance(user, dict) or type(user.get("id")) is not int or user["id"] <= 0:
            raise HTTPException(401, "Valid Telegram user is required")
        if users is None:
            raise HTTPException(503, "Mini App database unavailable")
        await users.mark_active(
            user["id"],
            username=user.get("username") if isinstance(user.get("username"), str) else None,
            first_name=user.get("first_name") if isinstance(user.get("first_name"), str) else None,
            last_name=user.get("last_name") if isinstance(user.get("last_name"), str) else None,
        )
        record = await users.get_by_telegram_id(user["id"])
        if record is None:
            raise HTTPException(503, "Mini App user unavailable")
        return record

    Identity = Annotated[User, Depends(current_user)]

    @router.get("/bootstrap")
    async def bootstrap(user: Identity) -> dict:
        passport = await users.get_visa_passport(user.id)
        countries = await visas.countries()
        return {
            "user": {
                "first_name": user.first_name or "مسافر",
                "username": user.username,
            },
            "passport": passport,
            "countries": [
                {"code": country.code, "name": persian_country(country.code, country.name)}
                for country in countries
            ],
            "links": {
                "support": support_url(settings.ticket_support_username),
                "cargo": "https://t.me/advertio_cargo",
                "bot": f"https://t.me/{settings.telegram_bot_username}",
            },
        }

    @router.post("/passport")
    async def set_passport(payload: PassportSelection, user: Identity) -> dict:
        if visas is None:
            raise HTTPException(503, "Visa service unavailable")
        # Countries displayed by the Mini App are from the validated dataset.
        if not await visas.rule(payload.passport, "IR") and not any(
            country.code == payload.passport for country in await visas.countries()
        ):
            raise HTTPException(422, "Passport not in the published catalog")
        await users.set_visa_passport(user.id, payload.passport)
        return {"passport": payload.passport}

    @router.get("/visa")
    async def visa_list(user: Identity, passport: str = "IR") -> dict:
        if not _CODE.fullmatch(passport):
            raise HTTPException(422, "Invalid passport")
        if visas is None:
            raise HTTPException(503, "Visa service unavailable")
        # The local index holds at most ~200 entries per passport. Fetch in
        # bounded pages instead of exposing the source's full raw documents.
        all_rules = []
        for page in range(10):
            items, count = await visas.listing(passport, page=page, page_size=30)
            all_rules.extend({
                "destination": item.destination,
                "country_name": persian_country(item.destination, item.country_name),
                "status": item.status,
                "stay_days": item.stay_days,
                "verified_on": item.verified_on,
            } for item in items)
            if len(all_rules) >= count or not items:
                break
        return {"passport": passport, "rules": all_rules}

    @router.get("/visa/rule")
    async def visa_rule(user: Identity, passport: str = "IR", destination: str = "") -> dict:
        if not _CODE.fullmatch(passport) or not _CODE.fullmatch(destination):
            raise HTTPException(422, "Invalid passport or destination")
        if visas is None:
            raise HTTPException(503, "Visa service unavailable")
        rule = await visas.rule(passport, destination)
        if rule is None:
            raise HTTPException(404, "Visa rule unavailable")
        result = asdict(rule)
        result["country_name"] = persian_country(rule.destination, rule.country_name)
        # Only explicitly HTTPS citations may be linked from the Mini App.
        if result["source_url"] and not result["source_url"].startswith("https://"):
            result["source_url"] = None
        return result

    @router.get("/useful")
    async def useful(user: Identity) -> dict:
        catalog = default_catalog()
        categories = []
        for key, title in _CATEGORIES:
            links = [
                {"title": item.title, "url": item.url, "description": item.description}
                for item in catalog.by_category(key) if item.url.startswith("https://")
            ]
            if links:
                categories.append({"id": key, "title": title, "links": links})
        return {"categories": categories}

    @router.get("/alerts")
    async def alert_list(user: Identity) -> dict:
        return {
            "prices": [asdict(item) for item in await prices.list_user_alerts(user.id)],
            "visa": [asdict(item) for item in await watches.list_user(user.id)],
        }

    @router.post("/alerts/prices", status_code=201)
    async def create_price_alert(payload: PriceAlertCreation, user: Identity) -> dict:
        if public_prices is None:
            raise HTTPException(503, "Ticket prices unavailable")
        origin, destination = payload.origin.strip(), payload.destination.strip()
        if not origin or not destination:
            raise HTTPException(422, "Route is required")
        if payload.kind == "percent":
            if payload.threshold_percent is None or payload.threshold_percent % 5 != 0:
                raise HTTPException(422, "Select a valid discount percentage")
            if payload.target_price_toman is not None:
                raise HTTPException(422, "Price and discount cannot be combined")
        elif payload.target_price_toman is None or payload.threshold_percent is not None:
            raise HTTPException(422, "Select a valid price ceiling")
        try:
            feed = await public_prices.get()
        except Exception as exc:
            raise HTTPException(503, "Ticket prices unavailable") from exc
        if feed["stale"]:
            raise HTTPException(409, "Ticket prices must be refreshed before creating an alert")
        if not any(
            route["origin"] == origin and any(
                item["name"] == destination for item in route["destinations"]
            )
            for route in feed["routes"]
        ):
            raise HTTPException(422, "Route is not in current ticket prices")
        try:
            saved = await prices.save_route(user.id, origin, destination)
            if payload.kind == "percent":
                result = await prices.create_percent(
                    user.id, saved.id, payload.threshold_percent
                )
            else:
                result = await prices.create(
                    user.id, saved.id, payload.target_price_toman, "TOMAN"
                )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"id": result.id, "created": True}

    @router.patch("/alerts/prices/{alert_id}")
    async def update_price_alert(alert_id: int, payload: PriceAlertStatus, user: Identity) -> dict:
        try:
            updated = await prices.set_user_status(user.id, alert_id, payload.status)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if not updated:
            raise HTTPException(404, "Price alert unavailable")
        return {"updated": True}

    @router.delete("/alerts/prices/{alert_id}")
    async def delete_price_alert(alert_id: int, user: Identity) -> dict:
        if not await prices.delete_user_alert(user.id, alert_id):
            raise HTTPException(404, "Price alert unavailable")
        return {"deleted": True}

    @router.post("/alerts/visa", status_code=201)
    async def create_visa_watch(payload: VisaWatchCreation, user: Identity) -> dict:
        try:
            result = await watches.subscribe(user.id, payload.passport, payload.destination)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"id": result.id, "active": result.active}

    @router.patch("/alerts/visa/{watch_id}")
    async def update_visa_watch(watch_id: int, payload: VisaWatchStatus, user: Identity) -> dict:
        try:
            changed = await watches.set_active(user.id, watch_id, payload.active)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if not changed:
            raise HTTPException(404, "Visa watch unavailable")
        return {"updated": True}

    @router.delete("/alerts/visa/{watch_id}")
    async def delete_visa_watch(watch_id: int, user: Identity) -> dict:
        if not await watches.remove(user.id, watch_id):
            raise HTTPException(404, "Visa watch unavailable")
        return {"deleted": True}

    return router
