"""Process health and privacy-safe runtime metrics."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RuntimeMetrics:
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    counters: dict[str, int] = field(default_factory=dict)

    def increment(self, name: str) -> None:
        self.counters[name] = self.counters.get(name, 0) + 1

    def snapshot(self) -> dict:
        return {"started_at": self.started_at.isoformat(), "counters": dict(self.counters)}


def healthcheck(database_url: str) -> dict[str, str]:
    return {"status": "ok", "database": "configured" if database_url else "missing"}
