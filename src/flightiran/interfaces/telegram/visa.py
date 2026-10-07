"""Escaped, source-backed visa rendering."""

from html import escape

from flightiran.modules.visa.knowledge import VisaProfile


def render_visa_profile(profile: VisaProfile | None) -> str:
    if profile is None:
        return "اطلاعات ویزا پیدا نشد یا منقضی شده است."
    warning = "\n⚠️ این اطلاعات منقضی شده است." if profile.is_expired else ""
    docs = ", ".join(escape(item) for item in profile.required_documents) or "ندارد"
    return (
        f"<b>{escape(profile.destination)}</b>\n"
        f"وضعیت: {escape(profile.status.value)}\n"
        f"مدارک: {docs}\n"
        f'منبع: <a href="{escape(profile.source_url)}">official source</a>\n'
        f"بررسی: {profile.checked_on.isoformat()} · نسخه {escape(profile.version)}{warning}"
    )
