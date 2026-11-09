"""Persistent, user-scoped travel checklist for the Telegram HTML widget."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from flightiran.db.engine import Database
from flightiran.db.models import TravelChecklist

# Stable bit positions: do not reorder them after shipping, or saved progress moves.
# (title, category index, short description, international only)
TASKS = (
    ("بلیت یا واچر", 0, "نسخه قابل نمایش در تلفن", False),
    ("کارت شناسایی", 0, "اصل کارت و اطلاعات هویتی", False),
    ("بیمه مسافرتی", 0, "در صورت نیاز سفر", False),
    ("گذرنامه معتبر", 0, "اعتبار مورد نیاز کشور مقصد", True),
    ("ویزا یا مجوز ورود", 0, "در صورت الزام مقصد", True),
    ("ساعت پرواز", 1, "تاریخ و زمان حرکت را بررسی کن", False),
    ("ترمینال و گیت", 1, "تغییرات لحظه آخری را بررسی کن", False),
    ("مسیر تا فرودگاه", 1, "برای ترافیک زمان در نظر بگیر", False),
    ("اقامت و نشانی", 1, "آدرس و تأییدیه رزرو", False),
    ("ارز و روش پرداخت", 1, "وجه نقد و کارت مناسب مقصد", True),
    ("چمدان و بار مجاز", 2, "وزن، ابعاد و قوانین ایرلاین", False),
    ("شارژر و پاوربانک", 2, "محدودیت حمل باتری را بررسی کن", False),
    ("داروهای شخصی", 2, "نسخه و قوانین حمل دارو", False),
    ("وسایل بهداشتی", 2, "لوازم ضروری و مایعات مجاز", False),
    ("اینترنت و رومینگ", 2, "سیم‌کارت یا اتصال مقصد", True),
)
MODES = ("d", "i")
VALID_BITS = {
    "d": sum(1 << index for index, task in enumerate(TASKS) if not task[3]),
    "i": (1 << len(TASKS)) - 1,
}


@dataclass(frozen=True)
class ChecklistState:
    mode: str = "d"
    domestic: int = 0
    international: int = 0
    revision: int = 0

    def as_json(self) -> str:
        """Compact enough for a Telegram widget's 1024-byte chat_data limit."""
        return json.dumps(
            {"m": self.mode, "d": self.domestic, "i": self.international,
             "v": self.revision},
            separators=(",", ":"),
        )

    def progress(self, mode: str | None = None) -> tuple[int, int]:
        selected = mode or self.mode
        mask = self.domestic if selected == "d" else self.international
        allowed = VALID_BITS[selected]
        return (mask & allowed).bit_count(), allowed.bit_count()


class SQLiteTravelChecklistService:
    """Atomic SQLite updates prevent concurrent taps from losing checked items."""

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _validate_user(telegram_id: int) -> None:
        if type(telegram_id) is not int or telegram_id <= 0:
            raise ValueError("Invalid Telegram user ID")

    @staticmethod
    def _read_row(row: TravelChecklist | None) -> ChecklistState:
        if row is None:
            return ChecklistState()
        return ChecklistState(
            mode=row.mode, domestic=row.domestic_bits,
            international=row.international_bits, revision=row.revision,
        )

    async def get(self, telegram_id: int) -> ChecklistState:
        self._validate_user(telegram_id)
        async with self.database.session() as session:
            row = await session.get(TravelChecklist, telegram_id)
            return self._read_row(row)

    async def apply(
        self, telegram_id: int, action: str, mode: str | None = None,
        task_index: int | None = None,
    ) -> ChecklistState:
        self._validate_user(telegram_id)
        if action not in {"mode", "toggle", "reset"} or mode not in MODES:
            raise ValueError("Invalid checklist action")
        if action == "toggle" and (
            type(task_index) is not int
            or task_index < 0
            or task_index >= len(TASKS)
            or not (VALID_BITS[mode] & (1 << task_index))
        ):
            raise ValueError("Task cannot be checked for this travel mode")

        async with self.database.session() as session:
            # Idempotent creation is safe under simultaneous widgets or bot restarts.
            await session.execute(
                sqlite_insert(TravelChecklist)
                .values(
                    telegram_id=telegram_id, mode="d", domestic_bits=0,
                    international_bits=0, revision=0,
                )
                .on_conflict_do_nothing(index_elements=[TravelChecklist.telegram_id])
            )
            values = {
                "mode": mode,
                "revision": TravelChecklist.revision + 1,
                "updated_at": datetime.now(timezone.utc),
            }
            column = (
                TravelChecklist.domestic_bits if mode == "d"
                else TravelChecklist.international_bits
            )
            if action == "reset":
                values["domestic_bits" if mode == "d" else "international_bits"] = 0
            elif action == "toggle":
                bit = 1 << task_index
                values["domestic_bits" if mode == "d" else "international_bits"] = case(
                    (column.op("&")(bit) == 0, column + bit),
                    else_=column - bit,
                )
            await session.execute(
                update(TravelChecklist)
                .where(TravelChecklist.telegram_id == telegram_id)
                .values(**values)
                .execution_options(synchronize_session=False)
            )
            row = await session.scalar(
                select(TravelChecklist).where(TravelChecklist.telegram_id == telegram_id)
            )
            return self._read_row(row)
