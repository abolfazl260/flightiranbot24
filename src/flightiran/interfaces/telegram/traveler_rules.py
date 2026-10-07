"""Telegram-safe traveler rule rendering."""

from html import escape

from flightiran.modules.traveler_rules.knowledge import RuleArticle


def render_rule(article: RuleArticle | None) -> str:
    if article is None:
        return "مقاله‌ای با این مشخصات پیدا نشد."
    warning = "\n⚠️ اعتبار این مطلب پایان یافته است." if article.expired else ""
    return (
        f"<b>{escape(article.title)}</b>\n{escape(article.body)}\n"
        f'منبع: <a href="{escape(article.source_url)}">{escape(article.source_url)}</a>\n'
        f"نسخه: {escape(article.version)} · بررسی: {article.checked_on.isoformat()}{warning}"
    )
