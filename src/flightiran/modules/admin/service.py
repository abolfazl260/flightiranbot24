"""Role/allowlist checks and privacy-safe reports."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:
    users: int = 0
    commands: int = 0
    flight_searches: int = 0
    visa_assessments: int = 0
    errors: int = 0
    conversions: int = 0


@dataclass(frozen=True)
class ReportPage:
    items: tuple[dict, ...]
    page: int
    has_next: bool


class AdminService:
    def __init__(self, allowlist: set[int]) -> None:
        self.allowlist = allowlist
        self.audit_events: list[dict] = []
        self.metrics = Metrics()

    def is_admin(self, user_id: int, roles: set[str] | None = None) -> bool:
        return user_id in self.allowlist or "admin" in (roles or set())

    def mutate(
        self, user_id: int, action: str, payload: dict | None = None, roles: set[str] | None = None
    ) -> None:
        if not self.is_admin(user_id, roles):
            raise PermissionError("admin access required")
        self.audit_events.append(
            {"user_id": user_id, "action": action, "keys": sorted((payload or {}).keys())}
        )

    def report(self, rows: list[dict], page: int = 0, page_size: int = 20) -> ReportPage:
        page = max(page, 0)
        start = page * page_size
        items = tuple(
            {
                key: value
                for key, value in row.items()
                if key not in {"token", "secret", "phone", "email"}
            }
            for row in rows[start : start + page_size]
        )
        return ReportPage(items, page, start + page_size < len(rows))
