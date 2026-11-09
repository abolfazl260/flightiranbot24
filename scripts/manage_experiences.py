"""Server-local moderation. No public administrator endpoint or client secret."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from sqlalchemy import select

from flightiran.db.engine import create_database
from flightiran.db.models import ExperienceReport, ExperienceTarget, TravelExperience
from flightiran.modules.experiences.persistent import SQLiteExperienceService


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["import", "queue", "show", "reports", "moderate", "resolve-report"]
    )
    parser.add_argument("--id", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--kind", choices=["user", "archive"])
    parser.add_argument("--state", choices=["approved", "rejected", "deleted"])
    parser.add_argument("--reason")
    parser.add_argument("--operator")
    parser.add_argument("--permission-evidence")
    parser.add_argument("--public-text-file", type=Path)
    parser.add_argument("--public-name")
    parser.add_argument("--target", action="append")
    args = parser.parse_args()
    if not 0 <= args.offset <= 10000:
        parser.error("--offset must be between 0 and 10000")
    db = create_database(os.environ["DATABASE_URL"])
    service = SQLiteExperienceService(db)
    try:
        if args.action == "import":
            print(await service.import_archive(Path("data/experiences/archive/github-168.v1.json")))
        elif args.action == "moderate":
            if not args.id or not args.state or not args.reason or not args.operator:
                parser.error("--id --state --reason --operator required")
            print(
                await service.moderate(
                    args.id, state=args.state, reason=args.reason, actor=args.operator,
                    consent_evidence=args.permission_evidence,
                    public_text=args.public_text_file.read_text()
                    if args.public_text_file else None,
                    display_name=args.public_name, targets=args.target,
                )
            )
        elif args.action == "resolve-report":
            if not args.id or not args.operator or not args.reason:
                parser.error("--id --reason --operator required")
            async with db.session() as session:
                report = await session.get(ExperienceReport, args.id)
                if not report:
                    parser.error("Report not found")
                report.status = "resolved"
                row = await session.get(TravelExperience, report.experience_id)
                service.audit(session, row, args.operator, "report-resolved", args.reason)
        else:
            async with db.session() as session:
                if args.action == "show":
                    if not args.id:
                        parser.error("--id required")
                    row = await session.get(TravelExperience, args.id)
                    if row is None:
                        parser.error("Experience not found")
                    targets = (
                        await session.scalars(select(ExperienceTarget.target).where(
                            ExperienceTarget.experience_id == row.id
                        ))
                    ).all()
                    output = {
                        "id": row.id, "kind": row.kind, "state": row.state,
                        "body": row.body, "public_text": row.public_text,
                        "consent": bool(row.consent), "display_name": row.display_name,
                        "rating": row.rating, "criteria": row.criteria,
                        "targets": list(targets), "travel_date": row.travel_date,
                        "archive_id": row.archive_id, "original_hash": row.original_hash,
                    }
                elif args.action == "reports":
                    rows = (
                        await session.scalars(select(ExperienceReport).where(
                            ExperienceReport.status == "open"
                        ).order_by(ExperienceReport.id).offset(args.offset).limit(101))
                    ).all()
                    output = {
                        "items": [{"id": r.id, "experience_id": r.experience_id,
                                   "reason": r.reason} for r in rows[:100]],
                        "next_offset": args.offset+100 if len(rows) > 100 else None,
                    }
                else:
                    statement = select(TravelExperience).where(TravelExperience.state == "pending")
                    if args.kind:
                        statement = statement.where(TravelExperience.kind == args.kind)
                    rows = (
                        await session.scalars(statement.order_by(TravelExperience.id)
                                              .offset(args.offset).limit(101))
                    ).all()
                    items = []
                    for row in rows[:100]:
                        targets = (
                            await session.scalars(select(ExperienceTarget.target).where(
                                ExperienceTarget.experience_id == row.id
                            ))
                        ).all()
                        items.append({
                            "id": row.id, "kind": row.kind, "body": row.body,
                            "consent": bool(row.consent), "display_name": row.display_name,
                            "rating": row.rating, "criteria": row.criteria,
                            "targets": list(targets), "travel_date": row.travel_date,
                            "archive_id": row.archive_id,
                        })
                    output = {
                        "items": items,
                        "next_offset": args.offset+100 if len(rows) > 100 else None,
                    }
                print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
