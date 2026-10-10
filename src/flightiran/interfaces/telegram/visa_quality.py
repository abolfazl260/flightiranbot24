"""Localized evidence labels and local synchronization freshness warnings."""

from __future__ import annotations

from datetime import timezone
from html import escape

from flightiran.modules.visa.freshness import VisaDataFreshness
from flightiran.modules.visa.provenance import VisaProvenance

LABELS = {
    "fa": {
        "fresh": "آخرین بررسی موفق فهرست داده‌ها توسط ربات",
        "stale": "هشدار: داده‌های محلی ویزا بیش از {hours} ساعت همگام‌سازی موفق نداشته‌اند. "
                 "ممکن است اطلاعات قدیمی باشند.",
        "unknown": "هشدار: زمان آخرین همگام‌سازی موفق اطلاعات ویزا مشخص نیست.",
        "local": "این زمان، تاریخ اعتبار مقررات یا تأیید رسمی منبع نیست.",
        "destination_government": "🏛️ مرجع دولتی کشور مقصد",
        "foreign_government": "🌐 مرجع دولتی کشور ثالث ({country})",
        "government_unverified_jurisdiction": "🏢 منبع دولتی؛ کشور صادرکننده تأیید نشده",
        "intergovernmental": "🌍 نهاد بین‌المللی",
        "airline_database": "✈️ پایگاه رسمی اطلاعات شرکت هواپیمایی",
        "unspecified": "📚 نوع و منشأ مرجع در داده‌ها تأیید نشده",
        "scope_row": "استناد اختصاصی پاسپورت انتخاب‌شده",
        "scope_policy": "استناد عمومی کشور مقصد؛ نه تأیید مستقل این پاسپورت",
        "note": "نوع منبع و کشور صادرکننده بر اساس اطلاعات منتشرکننده "
                "و دامنه شناخته‌شده طبقه‌بندی شده‌اند؛ این، تضمین صحت قانون نیست.",
    },
    "en": {
        "fresh": "Last successful bot dataset-index check",
        "stale": "Warning: the local visa dataset has not synchronized successfully "
                 "for over {hours} hours. Information may be outdated.",
        "unknown": "Warning: no successful local visa synchronization timestamp is available.",
        "local": "This is not an official rule verification or legal expiry date.",
        "destination_government": "🏛️ Destination government authority",
        "foreign_government": "🌐 Third-country government authority ({country})",
        "government_unverified_jurisdiction": "🏢 Government source; jurisdiction unverified",
        "intergovernmental": "🌍 Intergovernmental source",
        "airline_database": "✈️ Official airline-information database",
        "unspecified": "📚 Source type/jurisdiction not verified",
        "scope_row": "Passport-specific citation",
        "scope_policy": "General destination policy, not an independent passport check",
        "note": "Authority labels use publisher metadata and a conservative set of "
                "recognized government domains; they do not guarantee legal accuracy.",
    },
    "ar": {
        "fresh": "آخر فحص ناجح لفهرس البيانات بواسطة البوت",
        "stale": "تحذير: لم تنجح مزامنة بيانات التأشيرات المحلية منذ أكثر من "
                 "{hours} ساعة؛ ربما أصبحت قديمة.",
        "unknown": "تحذير: تاريخ آخر مزامنة ناجحة لبيانات التأشيرات غير معروف.",
        "local": "هذا ليس تاريخ تحقق رسمي من القوانين أو انتهاء صلاحيتها.",
        "destination_government": "🏛️ مرجع حكومي لبلد الوجهة",
        "foreign_government": "🌐 مرجع حكومي لدولة ثالثة ({country})",
        "government_unverified_jurisdiction": "🏢 مرجع حكومي لم يُتحقق من دولته",
        "intergovernmental": "🌍 مرجع حكومي دولي",
        "airline_database": "✈️ قاعدة بيانات رسمية لشركات الطيران",
        "unspecified": "📚 نوع المرجع أو دولته غير مؤكدين",
        "scope_row": "استشهاد خاص بجواز السفر",
        "scope_policy": "سياسة عامة للوجهة؛ ليست تحققاً خاصاً بهذا الجواز",
        "note": "تعتمد التصنيفات على بيانات الناشر ونطاقات حكومية معروفة؛ "
                "ولا تضمن صحة أحكام الدخول.",
    },
}


def _label(language: str, key: str) -> str:
    return LABELS.get(language, LABELS["en"])[key]


def render_freshness(
    value: VisaDataFreshness | None, language: str, *, brief: bool = False
) -> str:
    if value is None:
        return ""
    if value.status == "unknown":
        return "⚠️ " + escape(_label(language, "unknown"))
    if value.checked_at is None:
        return "⚠️ " + escape(_label(language, "unknown"))
    if value.status == "stale":
        return "⚠️ " + escape(
            _label(language, "stale").format(hours=value.threshold_hours)
        )
    # Successful manifest/index checks are not individual rule verification.
    checked = value.checked_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if brief:
        return ""
    return (
        "🗓 " + escape(_label(language, "fresh")) + ": "
        + escape(checked) + "\n<i>" + escape(_label(language, "local")) + "</i>"
    )


def render_authority(
    provenance: VisaProvenance, language: str, *, full: bool = False
) -> str:
    label = _label(language, provenance.authority)
    label = label.format(country=provenance.authority_country or "?")
    scope = _label(
        language, "scope_row" if provenance.source_level == "row" else "scope_policy"
    )
    lines = [escape(label), "🔎 " + escape(scope)]
    if full:
        lines.append("<i>" + escape(_label(language, "note")) + "</i>")
    return "\n".join(lines)
