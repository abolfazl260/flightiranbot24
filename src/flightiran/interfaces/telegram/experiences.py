"""Published review reader and explicit handoff to the authenticated Mini App."""

import re
from html import escape
from urllib.parse import urlencode, urlsplit, urlunsplit

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from flightiran.modules.experiences.persistent import TARGET, ExperienceError


def mini_url(url, target="", review=None):
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(
                {
                    "screen": "experiences",
                    "target": target,
                    **({"review": review} if review else {}),
                }
            ),
            "",
        )
    )


async def show_experiences(message, service, web_url, *, target="", offset=0, review=None):
    if service is None:
        await message.reply_text("تجربه‌ها فعلاً در دسترس نیستند.")
        return
    try:
        data = await service.public(target=target, offset=offset)
    except ExperienceError:
        await message.reply_text("زمینهٔ تجربه معتبر نیست.")
        return
    if review is not None:
        data["items"] = [r for r in await service.public_all() if r["id"] == review]
    stats = data["stats"]
    lines = ["<b>تجربه‌ها و رضایت مسافران</b>", "تجربهٔ شخصی؛ نه مقررات رسمی یا ارزیابی ایمنی."]
    if stats["rating_count"]:
        lines.append(f"رضایت: {stats['average']} از ۵ • {stats['rating_count']} رأی")
        if stats["low_sample"]:
            lines.append("نمونه کم است؛ برای رتبه‌بندی قابل اتکا نیست.")
    else:
        lines.append("هنوز رأی عددی تأییدشده‌ای ثبت نشده است.")
    buttons = []
    for row in data["items"]:
        lines.append(
            escape(row["display_name"]) + " • " + escape(row["posted_label"] or row["created_at"])
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    "متن کامل تجربهٔ " + row["display_name"], callback_data=f"xp:show:{row['id']}:0"
                )
            ]
        )
    if not data["items"]:
        lines.append("تجربهٔ دارای مجوز و تأیید انتشار برای این زمینه موجود نیست.")
    url = mini_url(web_url, target, review)
    if url and getattr(getattr(message, "chat", None), "type", None) == "private":
        buttons.append(
            [InlineKeyboardButton("ثبت، مدیریت، رأی و گزارش با ورود امن", web_app=WebAppInfo(url))]
        )
    else:
        lines.append("ثبت و مدیریت تجربه از مینی‌اپ رسمی ربات، پس از ورود تلگرام انجام می‌شود.")
    await message.reply_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_experience_callback(query, service):
    if service is None:
        await query.message.reply_text("تجربه‌ها فعلاً در دسترس نیستند.")
        return
    parts = query.data.split(":")
    if len(parts) != 4 or parts[1] != "show" or not parts[2].isdigit() or not parts[3].isdigit():
        return
    row = next((r for r in await service.public_all() if r["id"] == int(parts[2])), None)
    if row is None:
        await query.message.reply_text("این تجربه دیگر در فهرست منتشرشده نیست.")
        return
    page = int(parts[3])
    # Original public text is never dropped; page offsets select exact Unicode slices.
    pages = [row["text"][i : i + 1800] for i in range(0, len(row["text"]), 1800)]
    page = min(page, len(pages) - 1)
    buttons = []
    if page:
        buttons.append(
            InlineKeyboardButton("قبلی", callback_data=f"xp:show:{row['id']}:{page - 1}")
        )
    if page + 1 < len(pages):
        buttons.append(
            InlineKeyboardButton("بعدی", callback_data=f"xp:show:{row['id']}:{page + 1}")
        )
    await query.edit_message_text(
        escape(row["display_name"]) + "\n\n" + escape(pages[page]),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([buttons]),
    )


def start_target(payload):
    if payload == "experiences" or review_id(payload) is not None:
        return ""
    if payload.startswith("xp_"):
        value = payload[3:].replace("_", ":", 1)
        if TARGET.fullmatch(value):
            return value
    return None


def review_id(payload):
    match = re.fullmatch(r"xp_review_([1-9][0-9]{0,11})", payload)
    return int(match[1]) if match else None
