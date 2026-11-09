"""One public review contract; all mutations use verified Telegram identity."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from flightiran.db.models import User
from flightiran.modules.experiences.persistent import ExperienceError, SQLiteExperienceService


class ExperienceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    targets: list[str] = Field(min_length=1, max_length=10)
    body: str = Field(min_length=20, max_length=1500)
    rating: StrictInt | None = Field(default=None, ge=1, le=5)
    criteria: dict[str, StrictInt] = Field(default_factory=dict)
    consent: StrictBool
    display_name: str = Field(default="مسافر", max_length=80)
    travel_date: str | None = Field(default=None, max_length=10)


class VoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpful: StrictBool


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=40)


async def call(coro):
    try:
        return await coro
    except ExperienceError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, "Experiences unavailable") from exc


def public_router(database):
    router = APIRouter(prefix="/api/v1/experiences")
    service = SQLiteExperienceService(database) if database else None

    @router.get("")
    async def listing(
        response: Response,
        target: str = Query("", max_length=128),
        q: str = Query("", max_length=100),
        sort: str = "newest",
        offset: int = Query(0, ge=0, le=10000),
    ):
        if service is None:
            raise HTTPException(503, "Experiences unavailable")
        response.headers["Cache-Control"] = "no-store"
        return await call(service.public(target=target, search=q, sort=sort, offset=offset))

    @router.get("/{identifier}")
    async def detail(identifier: int):
        if service is None:
            raise HTTPException(503, "Experiences unavailable")
        row = next((r for r in await call(service.public_all()) if r["id"] == identifier), None)
        if row is None:
            raise HTTPException(404, "Experience not found")
        return row

    return router


def private_router(database, current_user):
    router = APIRouter(prefix="/experiences")
    service = SQLiteExperienceService(database) if database else None
    Identity = Annotated[User, Depends(current_user)]

    def available():
        if service is None:
            raise HTTPException(503, "Experiences unavailable")
        return service

    @router.get("/mine")
    async def own(user: Identity, offset: int = Query(0, ge=0, le=10000)):
        return await call(available().own(user.id, offset))

    @router.post("")
    async def submit(payload: ExperienceInput, user: Identity):
        return await call(available().submit(user.id, **payload.model_dump()))

    @router.patch("/{identifier}")
    async def edit(identifier: int, payload: ExperienceInput, user: Identity):
        return await call(available().update(user.id, identifier, **payload.model_dump()))

    @router.delete("/{identifier}")
    async def remove(identifier: int, user: Identity):
        return await call(available().update(user.id, identifier, remove=True))

    @router.post("/{identifier}/vote")
    async def vote(identifier: int, payload: VoteInput, user: Identity):
        return await call(available().interact(user.id, identifier, helpful=payload.helpful))

    @router.post("/{identifier}/report")
    async def report(identifier: int, payload: ReportInput, user: Identity):
        return await call(available().interact(user.id, identifier, report=payload.reason))

    return router
