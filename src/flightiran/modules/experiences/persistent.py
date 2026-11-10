"""Persistent publication gate. Private archive/origin/actor data never leaves this service."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jsonschema
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.sqlite import insert

from flightiran.db.models import (
    ExperienceAudit,
    ExperienceReport,
    ExperienceTarget,
    ExperienceVote,
    TravelExperience,
)

TARGET = re.compile(
    r"(?:airport:[A-Z]{3}|airline:[a-z0-9-]{2,80}|country:[A-Z]{2}"
    r"|route:[A-Z]{3}-[A-Z]{3}|flight:[A-Z0-9-]{2,16})\Z"
)
CRITERIA = {
    "airport": {"cleanliness", "signage", "queues", "services"},
    "airline": {
        "crew",
        "seat",
        "catering",
        "cleanliness",
        "delay_response",
        "checkin",
        "baggage",
        "value",
    },
}


class ExperienceError(ValueError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def targets_checked(targets: list[str]) -> list[str]:
    if not isinstance(targets, list) or not 1 <= len(targets) <= 10:
        raise ExperienceError("Choose one to ten travel contexts")
    if any(not isinstance(t, str) or not TARGET.fullmatch(t) for t in targets):
        raise ExperienceError("Invalid travel context")
    return sorted(set(targets))


def checked(body, rating, criteria, targets, consent, display_name, travel_date):
    if not isinstance(body, str) or not 20 <= len(body.strip()) or len(body) > 1500:
        raise ExperienceError("Experience text must contain 20..1500 characters")
    if rating is not None and (type(rating) is not int or not 1 <= rating <= 5):
        raise ExperienceError("Rating must be a real integer from 1 to 5")
    allowed = set().union(*(CRITERIA.get(t.split(":")[0], set()) for t in targets))
    if not isinstance(criteria, dict) or any(
        k not in allowed or type(v) is not int or not 1 <= v <= 5 for k, v in criteria.items()
    ):
        raise ExperienceError("Invalid context-specific rating")
    if type(consent) is not bool or not isinstance(display_name, str) or len(display_name) > 80:
        raise ExperienceError("Explicit publication choice and display name required")
    if travel_date:
        try:
            if date.fromisoformat(travel_date) > datetime.now(timezone.utc).date():
                raise ValueError
        except (ValueError, TypeError):
            raise ExperienceError("Invalid travel date") from None


class SQLiteExperienceService:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def visible():
        return (
            TravelExperience.state == "approved",
            TravelExperience.consent == 1,
            TravelExperience.public_text.is_not(None),
        )

    async def submit(
        self,
        owner: int,
        *,
        targets: list[str],
        body: str,
        rating=None,
        criteria=None,
        consent=False,
        display_name="مسافر",
        travel_date=None,
    ):
        targets = targets_checked(targets)
        criteria = criteria or {}
        checked(body, rating, criteria, targets, consent, display_name, travel_date)
        key = digest(str(owner) + json.dumps(targets) + body.strip().casefold())
        async with self.database.session() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            exists = await session.scalar(
                select(TravelExperience.id).where(TravelExperience.duplicate_key == key)
            )
            if exists:
                raise ExperienceError("Duplicate experience", 409)
            recent = await session.scalar(
                select(func.count())
                .select_from(TravelExperience)
                .where(
                    TravelExperience.owner_id == owner,
                    TravelExperience.created_at >= datetime.now(timezone.utc) - timedelta(hours=1),
                )
            )
            if recent >= 5:
                raise ExperienceError("Hourly submission limit reached", 429)
            row = TravelExperience(
                owner_id=owner,
                kind="user",
                duplicate_key=key,
                body=body,
                rating=rating,
                criteria=criteria,
                consent=int(consent),
                display_name=display_name,
                travel_date=travel_date,
                state="pending",
            )
            session.add(row)
            await session.flush()
            session.add_all([ExperienceTarget(experience_id=row.id, target=t) for t in targets])
            self.audit(session, row, str(owner), "submit", "Awaiting moderation")
            return {"id": row.id, "state": row.state}

    @staticmethod
    def audit(session, row, actor, action, reason):
        session.add(
            ExperienceAudit(
                experience_id=row.id,
                actor=actor,
                action=action,
                reason=reason,
                content_hash=digest(row.body),
            )
        )

    @staticmethod
    async def check_rate(session, owner, actions, limit):
        count = await session.scalar(
            select(func.count())
            .select_from(ExperienceAudit)
            .where(
                ExperienceAudit.actor == str(owner),
                ExperienceAudit.action.in_(actions),
                ExperienceAudit.created_at >= datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        if count >= limit:
            raise ExperienceError("Too many review actions; try later", 429)

    async def own(self, owner: int, offset: int = 0):
        async with self.database.session() as session:
            rows = (
                await session.scalars(
                    select(TravelExperience)
                    .where(TravelExperience.owner_id == owner)
                    .order_by(TravelExperience.id.desc())
                    .offset(offset)
                    .limit(11)
                )
            ).all()
            output = []
            for r in rows[:10]:
                targets = (
                    await session.scalars(
                        select(ExperienceTarget.target).where(
                            ExperienceTarget.experience_id == r.id
                        )
                    )
                ).all()
                output.append(
                    {
                        "id": r.id,
                        "body": r.body,
                        "rating": r.rating,
                        "criteria": r.criteria,
                        "targets": targets,
                        "consent": bool(r.consent),
                        "display_name": r.display_name,
                        "travel_date": r.travel_date,
                        "state": r.state,
                        "reason": r.moderation_reason,
                    }
                )
            return {"items": output, "next_offset": offset + 10 if len(rows) > 10 else None}

    async def update(self, owner: int, identifier: int, *, remove: bool = False, **values):
        async with self.database.session() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            row = await session.scalar(
                select(TravelExperience).where(
                    TravelExperience.id == identifier,
                    TravelExperience.owner_id == owner,
                    TravelExperience.kind == "user",
                )
            )
            if row is None:
                raise ExperienceError("Experience not found", 404)
            await self.check_rate(session, owner, ("edit", "delete"), 10)
            was_public = (
                row.state == "approved" and row.consent == 1 and row.public_text is not None
            )
            if remove:
                row.state, row.consent, row.public_text = "deleted", 0, None
            else:
                targets = targets_checked(values.pop("targets"))
                checked(
                    values["body"],
                    values.get("rating"),
                    values.get("criteria") or {},
                    targets,
                    values["consent"],
                    values["display_name"],
                    values.get("travel_date"),
                )
                key = digest(str(owner) + json.dumps(targets) + values["body"].strip().casefold())
                duplicate = await session.scalar(
                    select(TravelExperience.id).where(
                        TravelExperience.duplicate_key == key, TravelExperience.id != identifier
                    )
                )
                if duplicate:
                    raise ExperienceError("Duplicate experience", 409)
                values["criteria"] = values.get("criteria") or {}
                row.duplicate_key = key
                for name in ("body", "rating", "criteria", "display_name", "travel_date"):
                    setattr(row, name, values.get(name))
                row.consent = int(values["consent"])
                row.state, row.public_text = "pending", None
                await session.execute(
                    delete(ExperienceVote).where(ExperienceVote.experience_id == identifier)
                )
                await session.execute(
                    delete(ExperienceTarget).where(ExperienceTarget.experience_id == identifier)
                )
                session.add_all(
                    [ExperienceTarget(experience_id=identifier, target=t) for t in targets]
                )
            row.updated_at = datetime.now(timezone.utc)
            self.audit(session, row, str(owner), "delete" if remove else "edit", "Owner request")
            return {
                "id": row.id,
                "state": row.state,
                "experience_mutation": bool(was_public),
                "modified_at": row.updated_at.isoformat(),
            }

    async def moderate(
        self,
        identifier: int,
        *,
        state: str,
        reason: str,
        actor: str,
        consent_evidence: str | None = None,
        public_text: str | None = None,
        display_name: str | None = None,
        targets: list[str] | None = None,
    ):
        if (
            state not in {"approved", "rejected", "deleted"}
            or not reason.strip()
            or not actor.strip()
        ):
            raise ExperienceError("Moderation state, reason and operator identity required")
        async with self.database.session() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            row = await session.get(TravelExperience, identifier)
            if row is None:
                raise ExperienceError("Experience not found", 404)
            if state == "approved":
                if row.kind == "archive":
                    if (
                        not consent_evidence
                        or not consent_evidence.strip()
                        or not public_text
                        or not display_name
                        or len(display_name) > 80
                    ):
                        raise ExperienceError(
                            "Archive needs publication permission, reviewed text and name"
                        )
                    row.consent, row.consent_evidence = 1, consent_evidence
                    row.display_name = display_name
                elif not row.consent or row.state == "deleted":
                    raise ExperienceError("Owner publication consent missing")
                row.public_text = public_text if public_text is not None else row.body
                if not row.public_text.strip() or len(row.public_text) > 20000:
                    raise ExperienceError("Invalid public text")
            if targets is not None:
                targets = targets_checked(targets)
                await session.execute(
                    delete(ExperienceTarget).where(ExperienceTarget.experience_id == identifier)
                )
                session.add_all(
                    [ExperienceTarget(experience_id=identifier, target=t) for t in targets]
                )
            row.updated_at = datetime.now(timezone.utc)
            row.state, row.moderation_reason = state, reason
            if state != "approved":
                row.public_text = None
            self.audit(session, row, actor, state, reason)
            return {"id": identifier, "state": state}

    async def public_all(self):
        async with self.database.session() as session:
            rows = (
                await session.scalars(
                    select(TravelExperience)
                    .where(*self.visible())
                    .order_by(TravelExperience.id.desc())
                    .limit(1001)
                )
            ).all()
            if len(rows) > 1000:
                raise ExperienceError("Public projection requires pagination expansion", 503)
            ids = [r.id for r in rows]
            targets, votes = {}, {}
            if ids:
                for identifier, target in (
                    await session.execute(
                        select(ExperienceTarget.experience_id, ExperienceTarget.target).where(
                            ExperienceTarget.experience_id.in_(ids)
                        )
                    )
                ).all():
                    targets.setdefault(identifier, []).append(target)
                votes = dict(
                    (
                        await session.execute(
                            select(ExperienceVote.experience_id, func.count()).group_by(
                                ExperienceVote.experience_id
                            )
                        )
                    ).all()
                )
            return [
                {
                    "id": r.id,
                    "kind": r.kind,
                    "text": r.public_text,
                    "display_name": r.display_name,
                    "rating": r.rating,
                    "criteria": r.criteria,
                    "targets": sorted(targets.get(r.id, [])),
                    "posted_label": r.posted_label,
                    "travel_date": r.travel_date,
                    "modified_at": r.updated_at.replace(tzinfo=timezone.utc).isoformat(),
                    "created_at": r.created_at.isoformat() + "Z"
                    if r.created_at.tzinfo is None
                    else r.created_at.isoformat(),
                    "helpful": votes.get(r.id, 0),
                }
                for r in rows
            ]

    async def public(self, *, target="", search="", sort="newest", offset=0):
        if target and not TARGET.fullmatch(target):
            raise ExperienceError("Invalid travel context")
        if (
            sort not in {"newest", "helpful", "rating"}
            or not 0 <= offset <= 10000
            or len(search) > 100
        ):
            raise ExperienceError("Invalid experience filter")
        rows = [
            r
            for r in await self.public_all()
            if (not target or target in r["targets"]) and search.lower() in r["text"].lower()
        ]
        ratings = [r["rating"] for r in rows if type(r["rating"]) is int]
        # Rating comparisons require five actual approved numeric votes.
        if sort == "rating" and len(ratings) < 5:
            sort = "newest"
        rows.sort(
            key=lambda r: (
                r["helpful"]
                if sort == "helpful"
                else (r["rating"] or 0)
                if sort == "rating"
                else r["id"],
                r["id"],
            ),
            reverse=True,
        )
        return {
            "items": rows[offset : offset + 10],
            "next_offset": offset + 10 if offset + 10 < len(rows) else None,
            "stats": {
                "criteria": {
                    key: {
                        "count": len(votes),
                        "average": math.floor(sum(votes) * 100 / len(votes) + 0.5) / 100,
                        "low_sample": len(votes) < 5,
                    }
                    for key in sorted(set().union(*CRITERIA.values()))
                    if (votes := [r["criteria"][key] for r in rows if key in r["criteria"]])
                },
                "rating_count": len(ratings),
                "average": math.floor(sum(ratings) * 100 / len(ratings) + 0.5) / 100
                if ratings
                else None,
                "low_sample": 0 < len(ratings) < 5,
                "comparison_allowed": len(ratings) >= 5,
            },
        }

    async def interact(self, owner, identifier, *, helpful=None, report=None):
        async with self.database.session() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            row = await session.scalar(
                select(TravelExperience).where(TravelExperience.id == identifier, *self.visible())
            )
            if row is None:
                raise ExperienceError("Experience not found", 404)
            await self.check_rate(session, owner, ("helpful", "report"), 60)
            if report is not None:
                if report not in {"spam", "privacy", "abuse", "inaccurate", "other"}:
                    raise ExperienceError("Invalid report reason")
                await session.execute(
                    insert(ExperienceReport)
                    .values(experience_id=identifier, user_id=owner, reason=report)
                    .on_conflict_do_nothing()
                )
            else:
                if row.owner_id == owner:
                    raise ExperienceError("Self-voting is not allowed")
                if type(helpful) is not bool:
                    raise ExperienceError("Explicit vote required")
                if helpful:
                    await session.execute(
                        insert(ExperienceVote)
                        .values(experience_id=identifier, user_id=owner)
                        .on_conflict_do_nothing()
                    )
                else:
                    await session.execute(
                        delete(ExperienceVote).where(
                            ExperienceVote.experience_id == identifier,
                            ExperienceVote.user_id == owner,
                        )
                    )
            self.audit(
                session,
                row,
                str(owner),
                "report" if report else "helpful",
                report or "Explicit helpful vote",
            )
            return {"ok": True}

    async def import_archive(self, path: Path):
        data = json.loads(path.read_text())
        schema = json.loads(path.with_name("schema.v1.json").read_text())
        jsonschema.validate(data, schema)
        if len({r["archive_id"] for r in data["records"]}) != 51 or [
            r["order"] for r in data["records"]
        ] != list(range(1, 52)):
            raise ExperienceError("Archive IDs and source order must be complete and unique")
        for block in data["blocks"]:
            joined = "".join(
                r["raw_message"]
                for r in data["records"]
                if r["source_comment_id"] == block["comment_id"]
            )
            if joined != block["verbatim"] or digest(joined) != block["sha256"]:
                raise ExperienceError("Source block round-trip mismatch")
        async with self.database.session() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            for record in data["records"]:
                if digest(record["raw_message"]) != record["sha256"]:
                    raise ExperienceError("Archive content hash mismatch")
                old = await session.scalar(
                    select(TravelExperience).where(
                        TravelExperience.archive_id == record["archive_id"]
                    )
                )
                if old:
                    if old.original_hash != record["sha256"] or old.raw_source != record:
                        raise ExperienceError("Refusing to rewrite immutable archive")
                    continue
                row = TravelExperience(
                    kind="archive",
                    archive_id=record["archive_id"],
                    raw_source=record,
                    original_hash=record["sha256"],
                    duplicate_key=digest("archive:" + record["archive_id"]),
                    body=record["raw_message"],
                    display_name="مسافر",
                    posted_label=record["posted_label"],
                    state="pending",
                    consent=0,
                    rating=None,
                    criteria={},
                )
                session.add(row)
                await session.flush()
                self.audit(
                    session, row, "archive-import", "import", "Withheld pending permission review"
                )
        return 51
