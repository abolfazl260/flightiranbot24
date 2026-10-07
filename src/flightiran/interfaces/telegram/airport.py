"""Paginated airport selection and board rendering."""

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.airport.domain import AirportBoard, BoardStatus


def airport_keyboard(airports, page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
    page = max(page, 0)
    items = airports[page * page_size : (page + 1) * page_size]
    rows = [
        [
            InlineKeyboardButton(
                escape(airport.display_name("fa")), callback_data=f"airport:{airport.code}"
            )
        ]
        for airport in items
    ]
    navigation = []
    if page:
        navigation.append(InlineKeyboardButton("◀️", callback_data=f"airports:page:{page - 1}"))
    if (page + 1) * page_size < len(airports):
        navigation.append(InlineKeyboardButton("▶️", callback_data=f"airports:page:{page + 1}"))
    if navigation:
        rows.append(navigation)
    return InlineKeyboardMarkup(rows)


def render_board(board: AirportBoard, language: str = "fa") -> str:
    title = escape(board.airport.display_name(language))
    if board.status == BoardStatus.ERROR:
        return f"<b>{title}</b>\nخطا در دریافت اطلاعات. لطفاً بعداً دوباره تلاش کنید."
    if board.status == BoardStatus.STALE:
        prefix = "اطلاعات ممکن است قدیمی باشد.\n"
    else:
        prefix = ""
    if not board.flights:
        return f"<b>{title}</b>\n{prefix}پروازی برای نمایش پیدا نشد."
    lines = [f"<b>{title}</b>", prefix.rstrip()]
    lines.extend(
        f"{escape(flight.flight_number)} | {escape(flight.airline)} | "
        f"{escape(flight.status or 'N/A')}"
        for flight in board.flights
    )
    return "\n".join(line for line in lines if line)
