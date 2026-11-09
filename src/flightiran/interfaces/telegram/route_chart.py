"""Route-specific fare history charts using *only* recorded SQLite snapshots."""

from __future__ import annotations

import logging
import zlib
from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Protocol

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.db.repositories import RouteDailyMinimum

LOGGER = logging.getLogger(__name__)
CHART_DAYS = 21
PAGE_SIZE = 14


class RouteChartHistory(Protocol):
    async def list_chart_routes(self, *, days: int = 21) -> list[tuple[str, str]]: ...

    async def get_route_daily_minimums(
        self, origin: str, destination: str, *, days: int = 21
    ) -> list[RouteDailyMinimum]: ...


def _fa(value: object) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _toman(value: int) -> str:
    return _fa(f"{value:,}").replace(",", "٬")


def render_route_chart_html(
    origin: str, destination: str, samples: list[RouteDailyMinimum],
    *, as_of: date | None = None,
) -> str:
    """Render one SVG point per real daily minimum, without interpolating gaps."""
    if not samples:
        raise ValueError("Cannot draw a chart without recorded history")
    samples = sorted(samples, key=lambda entry: entry.day)
    if len({entry.day for entry in samples}) != len(samples):
        raise ValueError("Daily minima must have unique dates")
    if len(samples) > CHART_DAYS or any(entry.min_price_toman <= 0 for entry in samples):
        raise ValueError("Invalid chart samples")

    # Dates retain true calendar spacing over a 21-day period ending on the
    # newest observed day. Missing days are not represented as chart points.
    end_day = as_of or datetime.now(timezone.utc).date()
    start_day: date = end_day - timedelta(days=CHART_DAYS - 1)
    if samples[0].day < start_day or samples[-1].day > end_day:
        raise ValueError("Chart observations are outside the selected period")
    lo = min(entry.min_price_toman for entry in samples)
    hi = max(entry.min_price_toman for entry in samples)
    spread = hi - lo
    def x(entry: RouteDailyMinimum) -> float:
        return 22 + (entry.day - start_day).days * 13.6

    def y(entry: RouteDailyMinimum) -> float:
        return 103 - ((entry.min_price_toman - lo) * 66 / spread) if spread else 70
    paths: list[str] = []
    dots: list[str] = []
    for idx, entry in enumerate(samples):
        px, py = x(entry), y(entry)
        if idx and (entry.day - samples[idx - 1].day).days == 1:
            paths.append(
                f'<path d="M{x(samples[idx - 1]):.1f},{y(samples[idx - 1]):.1f}'
                f' L{px:.1f},{py:.1f}" stroke="#159979" stroke-width="2.7" '
                'fill="none"/>'
            )
        details = escape(f"{entry.day.isoformat()} UTC: {_toman(entry.min_price_toman)} تومان")
        dots.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.1" fill="#159979">'
            f"<title>{details}</title></circle>"
        )
    first = samples[0].day
    total_observations = sum(entry.sample_count for entry in samples)
    last_updated = samples[-1].last_captured_at.strftime("%Y-%m-%d %H:%M")
    trend_note = "تنها یک روز داده موجود است؛ هنوز روند قابل محاسبه نیست. " if len(samples) < 2 else ""
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><style>
body{{margin:0;padding:12px;font-family:Arial,sans-serif;
color:var(--tg-theme-text-color,#222);background:var(--tg-theme-bg-color,#fff)}}
h3{{margin:0 0 6px;font-size:17px}}
.note{{font-size:12px;line-height:1.75;color:var(--tg-theme-hint-color,#778)}}
svg{{width:100%;height:auto;display:block;margin:9px 0}}
.stats{{display:flex;gap:10px;margin:10px 0}}
.stat{{flex:1;background:var(--tg-theme-secondary-bg-color,#f0f2f4);
border-radius:10px;padding:9px 6px;text-align:center;font-size:12px}}
.stat strong{{display:block;margin-top:4px;font-size:13px}}
</style></head><body>
<h3>نمودار قیمت: {escape(origin)} ← {escape(destination)}</h3>
<div class="note">کمترین قیمت واقعی ثبت‌شده در هر روز • تومان • UTC</div>
<svg viewBox="0 0 320 145" xmlns="http://www.w3.org/2000/svg"
role="img" aria-label="نمودار قیمت ۲۱ روز گذشته">
<path d="M22 30H294 M22 70H294 M22 110H294" stroke="currentColor"
stroke-opacity=".13" stroke-dasharray="3,4" fill="none"/>
{''.join(paths)}{''.join(dots)}
<text x="22" y="15" fill="currentColor" font-size="11">{escape(_toman(hi))}</text>
<text x="22" y="122" fill="currentColor" font-size="11">{escape(_toman(lo))}</text>
<text x="22" y="140" fill="currentColor" font-size="10">{_fa(start_day.strftime('%m/%d'))}</text>
<text x="294" y="140" text-anchor="end" fill="currentColor" font-size="10">
{_fa(end_day.strftime('%m/%d'))}</text></svg>
<div class="stats">
<div class="stat">کمترین قیمت<strong>{_toman(lo)}</strong></div>
<div class="stat">بیشترین قیمت<strong>{_toman(hi)}</strong></div></div>
<div class="note">روزهای دارای داده: {_fa(len(samples))} از {_fa(CHART_DAYS)}
• تعداد ثبت‌ها: {_fa(total_observations)}</div>
<div class="note">اولین روز ثبت: {_fa(first.isoformat())}
• آخرین ثبت: {_fa(last_updated)} UTC</div>
<div class="note">روزهای بدون ثبت، نقطه یا خط تخمینی ندارند.
{trend_note}این نمودار قیمت لحظه‌ای رزرو نیست.</div>
</body></html>"""
    raw = html.encode("utf-8")
    if len(raw) > 32768 or len(zlib.compress(raw, level=9)) > 4096:
        raise ValueError("Chart HTML exceeds Telegram's widget size limits")
    return html


def _keypad(values: list[str], kind: str, page: int) -> InlineKeyboardMarkup:
    end_page = max(0, (len(values) - 1) // PAGE_SIZE)
    page = min(max(page, 0), end_page)
    start = page * PAGE_SIZE
    rows = [
        [InlineKeyboardButton(values[i], callback_data=f"chart:{kind}:{i}")
         for i in range(j, min(j + 2, start + PAGE_SIZE, len(values)))]
        for j in range(start, min(start + PAGE_SIZE, len(values)), 2)
    ]
    controls = []
    if page:
        controls.append(InlineKeyboardButton(
            "قبلی", callback_data=f"chart:{kind}s:{page - 1}"
        ))
    if page < end_page:
        controls.append(InlineKeyboardButton(
            "بعدی", callback_data=f"chart:{kind}s:{page + 1}"
        ))
    if controls:
        rows.append(controls)
    rows.append([InlineKeyboardButton("بازگشت به انتخاب مبدأ",
                                      callback_data="chart:start")])
    return InlineKeyboardMarkup(rows)


def _origins(routes: list[tuple[str, str]]) -> list[str]:
    return sorted({origin for origin, _ in routes})


def _destinations(routes: list[tuple[str, str]], origin: str) -> list[str]:
    return sorted({dest for source, dest in routes if source == origin})


async def _show(target: object, text: str, keyboard: InlineKeyboardMarkup) -> None:
    if hasattr(target, "edit_message_text"):
        await target.edit_message_text(text, reply_markup=keyboard)
    else:
        await target.reply_text(text, reply_markup=keyboard)


async def open_chart_picker(
    target: object, bot: object, history: RouteChartHistory | None,
    user_data: dict,
) -> None:
    """Choose from routes with retained observations, not invented city pairs."""
    chat = getattr(target, "message", target)
    if getattr(bot, "platform", "telegram") == "bale" or (
        getattr(getattr(chat, "chat", None), "type", None) != "private"
    ):
        await chat.reply_text("نمودار مسیر فقط در چت خصوصی تلگرام در دسترس است.")
        return
    if history is None:
        await chat.reply_text("تاریخچه قیمت بلیت در حال حاضر فعال نیست.")
        return
    try:
        routes = await history.list_chart_routes(days=CHART_DAYS)
    except Exception as exc:
        LOGGER.warning("route_chart_routes_failed type=%s", type(exc).__name__)
        await chat.reply_text("دریافت مسیرهای ثبت‌شده ممکن نیست.")
        return
    user_data["route_chart_routes"] = routes
    user_data.pop("route_chart_origin", None)
    if not routes:
        await chat.reply_text("هنوز هیچ مسیر دارای تاریخچه قیمت در ۲۱ روز اخیر ثبت نشده.")
        return
    await _show(target, "مبدأ را برای نمودار قیمت ۲۱ روزه انتخاب کنید:",
                _keypad(_origins(routes), "origin", 0))


async def handle_chart_callback(
    query: object, context: object, history: RouteChartHistory | None,
) -> None:
    """User-scoped route indices; all database queries use validated selections."""
    data = query.data or ""
    user_data = context.user_data
    if data == "chart:start":
        await open_chart_picker(query, context.bot, history, user_data)
        return
    if getattr(context.bot, "platform", "telegram") == "bale" or (
        getattr(getattr(query, "message", None), "chat", None) is None
        or query.message.chat.type != "private"
    ):
        return
    routes: list[tuple[str, str]] = user_data.get("route_chart_routes") or []
    if not routes:
        await query.edit_message_text(
            "فهرست مسیرها منقضی شده است. برای انتخاب دوباره /chart را بفرستید."
        )
        return
    origins = _origins(routes)
    parts = data.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await query.edit_message_text("انتخاب نامعتبر است. دوباره /chart را بفرستید.")
        return
    kind, index = parts[1], int(parts[2])
    if kind == "origins":
        await _show(query, "مبدأ را انتخاب کنید:", _keypad(origins, "origin", index))
        return
    if kind == "origin":
        if not 0 <= index < len(origins):
            await query.edit_message_text("مبدأ معتبر نیست. دوباره /chart را بفرستید.")
            return
        origin = origins[index]
        user_data["route_chart_origin"] = origin
        options = _destinations(routes, origin)
        await _show(query, f"مقصد پرواز از {origin} را انتخاب کنید:",
                    _keypad(options, "dest", 0))
        return

    origin = user_data.get("route_chart_origin")
    destinations = _destinations(routes, origin) if origin in origins else []
    if kind == "dests":
        await _show(query, f"مقصد پرواز از {origin} را انتخاب کنید:",
                    _keypad(destinations, "dest", index))
        return
    if kind != "dest" or not 0 <= index < len(destinations):
        await query.edit_message_text("مقصد معتبر نیست. دوباره /chart را بفرستید.")
        return
    destination = destinations[index]
    if history is None:
        await query.edit_message_text("تاریخچه قیمت در دسترس نیست.")
        return
    try:
        samples = await history.get_route_daily_minimums(
            origin, destination, days=CHART_DAYS
        )
        if not samples:
            await query.edit_message_text(
                "برای این مسیر دیگر داده ثبت‌شده در ۲۱ روز اخیر وجود ندارد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("انتخاب مسیر دیگر", callback_data="chart:start")
                ]]),
            )
            return
        html = render_route_chart_html(origin, destination, samples)
        await context.bot._post("sendWidget", {
            "chat_id": query.message.chat_id,
            "html": html,
            "caption": f"نمودار قیمت ثبت‌شده: {origin} ← {destination}",
        })
    except Exception as exc:
        LOGGER.warning("route_chart_send_failed type=%s", type(exc).__name__)
        await query.message.reply_text(
            "نمایش نمودار امکان‌پذیر نشد؛ داده‌های ثبت‌شده تغییر نکردند."
        )
        return
    await query.edit_message_text(
        f"نمودار واقعی {origin} ← {destination} ارسال شد.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("انتخاب مسیر دیگر", callback_data="chart:start")
        ]]),
    )
