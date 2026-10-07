"""Small process-local TTL cache for provider responses."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    expires_at: float
    value: T


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float = 30.0, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        if len(self._entries) >= self.max_entries and key not in self._entries:
            self._entries.pop(next(iter(self._entries)))
        self._entries[key] = _Entry(time.monotonic() + self.ttl_seconds, value)

    def clear(self) -> None:
        self._entries.clear()
