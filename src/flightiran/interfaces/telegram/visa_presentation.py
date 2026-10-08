"""Localized, safely escaped Telegram visa cards and native rich reports."""

from __future__ import annotations

from html import escape

from babel import Locale
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.visa.catalog import STATUS_GROUPS, Country, VisaDetail, VisaRule
from flightiran.modules.visa.provenance import (
    VisaProvenance,
    link_html,
    safe_source_url,
    source_date,
    visa_provenance,
)

LANG = {
    "fa": {
        "title": "🛂 راهنمای ویزا و ورود", "choose_passport": "پاسپورت خود را انتخاب کنید",
        "choose_destination": "کشور مقصد را انتخاب کنید", "passport": "پاسپورت",
        "destination": "مقصد", "status": "وضعیت ویزا", "stay": "مدت اقامت",
        "not_known": "در منبع مشخص نشده", "more": "جزئیات ویزا و شرایط ورود",
        "source": "منبع رسمی / منتشرکننده", "checked": "آخرین بررسی منبع",
        "policy": "استناد در سطح سیاست کشور؛ نه تأیید مستقل این پاسپورت",
        "row": "استناد اختصاصی این پاسپورت", "caution": (
            "این نتیجه عمومی است. نوع پاسپورت، اقامت کشور ثالث، مدارک پشتیبان، "
            "هدف سفر و ترانزیت ممکن است نتیجه را تغییر دهند. پیش از رزرو، "
            "مقررات نهاد رسمی مقصد و شرکت هواپیمایی را بررسی کنید."
        ),
        "residence": "اقامت انتخاب‌شده", "purpose": "هدف سفر",
        "residence_button": "تعیین کشور اقامت", "clear_residence": "حذف اقامت",
        "unmodeled": "این منبع اثر اقامت یا هدف خاص سفر را به‌طور کامل محاسبه نمی‌کند.",
        "intro": "اطلاعات ۱۹۹ مقصد، براساس پاسپورت و منابع استنادی. "
        "برای شروع پاسپورت را انتخاب کنید یا دستور /visa AF TR را بفرستید.",
        "empty": "دیتاست هنوز دریافت نشده است. مدیر می‌تواند /visa_sync را اجرا کند.",
        "missing": "برای این ترکیب داده معتبری در دیتابیس موجود نیست.",
        "another": "تغییر مقصد", "passports": "انتخاب پاسپورت",
        "list": "کشورهای قابل سفر براساس نوع ویزا", "all": "همه کشورها",
        "free": "بدون ویزا", "evisa": "ویزای الکترونیکی / ETA",
        "arrival": "ویزای فرودگاهی", "required": "ویزای قبلی / سفارتی",
        "other": "سایر / نامشخص", "back": "بازگشت",
        "search": "جست‌وجوی کشور", "search_hint": (
            "نام کشور یا کد دوحرفی آن را ارسال کنید؛ مثال: Turkey یا TR. "
            "برای توقف /cancel را بفرستید."
        ),
        "no_search": "کشوری با این نام پیدا نشد. کد ISO را هم می‌توانید وارد کنید.",
        "details": "گزارش کامل ریچ تکست", "entry": "مدارک و شرایط ورود",
        "types": "انواع ویزا و درخواست", "facts": "اطلاعات کاربردی کشور",
        "tips": "هشدارها و نکات", "faq": "پرسش‌های متداول",
        "sources": "منابع و تاریخ بررسی", "transit": "ترانزیت و ورود",
        "summary": "خلاصه نتیجه", "fee": "هزینه", "processing": "زمان پردازش",
        "validity": "اعتبار ویزا", "entries": "دفعات ورود",
        "apply": "درخواست ویزا", "docs": "مدارک لازم",
        "condition": "شرایط ویژه و استثناها", "unknown_warning": (
            "ثبت نشدن یک الزام به معنی معافیت از آن نیست."
        ),
        "license": "TravelRequirements.info · AXG Sp. z o.o. · CC BY 4.0 · اقتباس و ترجمه",
        "purpose_tourism": "گردشگری", "purpose_business": "تجاری",
        "purpose_transit": "ترانزیت", "filter": "فیلتر",
        "more_results": "صفحه", "no_items": "رکوردی برای این دسته پیدا نشد.",
        "search_results": "نتایج جست‌وجو", "unknown": "نامشخص",
    },
    "en": {
        "title": "🛂 Visa & entry guide", "choose_passport": "Select your passport",
        "choose_destination": "Select your destination", "passport": "Passport",
        "destination": "Destination", "status": "Visa requirement", "stay": "Stay",
        "not_known": "Not stated by source", "more": "Visa & entry details",
        "source": "Official/published source", "checked": "Source last verified",
        "policy": "Destination-policy citation, not an independent passport check",
        "row": "Passport-specific citation", "caution": (
            "This is general guidance. Passport class, third-country residence, supporting "
            "documents, travel purpose and transit can change eligibility. Verify the "
            "official destination and airline requirements before booking."
        ),
        "residence": "Declared residence", "purpose": "Travel purpose",
        "residence_button": "Specify residence", "clear_residence": "Clear residence",
        "unmodeled": (
            "This dataset does not fully calculate residence or special-purpose eligibility."
        ),
        "intro": "Information for 199 destinations, grouped by passport and sources. "
        "Choose a passport or try /visa AF TR.",
        "empty": "Visa data not yet imported. An administrator can run /visa_sync.",
        "missing": "No validated local data for this passport/destination.",
        "another": "Other destination", "passports": "Choose passport",
        "list": "Destinations by visa type", "all": "All destinations",
        "free": "Visa-free", "evisa": "eVisa / ETA",
        "arrival": "Visa on arrival", "required": "Advance / embassy visa",
        "other": "Other / unknown", "back": "Back",
        "search": "Search country", "search_hint": (
            "Send a country name or ISO two-letter code, e.g. Turkey or TR. "
            "Send /cancel to stop."
        ),
        "no_search": "Country not found. You can also use its ISO code.",
        "details": "Full rich-text report", "entry": "Documents & entry rules",
        "types": "Visa types & application", "facts": "Destination facts",
        "tips": "Travel advisories", "faq": "Frequently asked questions",
        "sources": "Sources & verification", "transit": "Transit and entry",
        "summary": "Overview", "fee": "Fee", "processing": "Processing",
        "validity": "Visa validity", "entries": "Entries",
        "apply": "Apply", "docs": "Required documents",
        "condition": "Special conditions and waivers", "unknown_warning": (
            "No published requirement is not proof of exemption."
        ),
        "license": "TravelRequirements.info · AXG Sp. z o.o. · CC BY 4.0 · adapted",
        "purpose_tourism": "Tourism", "purpose_business": "Business",
        "purpose_transit": "Transit", "filter": "Filter",
        "more_results": "Page", "no_items": "No entries in this category.",
        "search_results": "Search results", "unknown": "Unknown",
    },
    "ar": {
        "title": "🛂 دليل التأشيرات والدخول", "choose_passport": "اختر جواز سفرك",
        "choose_destination": "اختر بلد الوجهة", "passport": "جواز السفر",
        "destination": "الوجهة", "status": "متطلبات التأشيرة", "stay": "مدة الإقامة",
        "not_known": "غير مذكور في المصدر", "more": "تفاصيل التأشيرة والدخول",
        "source": "المصدر الرسمي / الناشر", "checked": "آخر تحقق من المصدر",
        "policy": "مرجع سياسة الوجهة، وليس تحققاً فردياً من الجواز",
        "row": "مرجع خاص بجواز السفر", "caution": (
            "معلومات عامة؛ قد تختلف الشروط حسب نوع الجواز والإقامة في بلد آخر "
            "والوثائق والغرض من السفر والعبور. تحقق من السلطات الرسمية وشركة الطيران."
        ),
        "residence": "بلد الإقامة المعلن", "purpose": "الغرض من السفر",
        "residence_button": "تحديد بلد الإقامة", "clear_residence": "حذف الإقامة",
        "unmodeled": "لا يحسب هذا المصدر جميع استثناءات الإقامة وأغراض السفر.",
        "intro": "بيانات ١٩٩ وجهة حسب جواز السفر والمصادر. اختر الجواز أو أرسل /visa AF TR.",
        "empty": "لم تُستورد بيانات التأشيرات بعد. يمكن للمشرف تشغيل /visa_sync.",
        "missing": "لا توجد بيانات محلية موثوقة لهذا المسار.",
        "another": "وجهة أخرى", "passports": "اختيار الجواز",
        "list": "الدول بحسب نوع التأشيرة", "all": "جميع الوجهات",
        "free": "بدون تأشيرة", "evisa": "تأشيرة إلكترونية / ETA",
        "arrival": "تأشيرة عند الوصول", "required": "تأشيرة مسبقة / سفارة",
        "other": "أخرى / غير معروف", "back": "عودة",
        "search": "البحث عن دولة", "search_hint": (
            "أرسل اسم الدولة أو رمز ISO مثل Turkey أو TR. أرسل /cancel للإلغاء."
        ),
        "no_search": "لم يتم العثور على الدولة. جرّب رمز ISO.",
        "details": "تقرير غني كامل", "entry": "الوثائق وشروط الدخول",
        "types": "أنواع التأشيرات والتقديم", "facts": "معلومات البلد",
        "tips": "تنبيهات ونصائح", "faq": "الأسئلة الشائعة",
        "sources": "المصادر وتاريخ التحقق", "transit": "العبور والدخول",
        "summary": "ملخص", "fee": "الرسوم", "processing": "مدة المعالجة",
        "validity": "صلاحية التأشيرة", "entries": "عدد مرات الدخول",
        "apply": "التقديم", "docs": "الوثائق المطلوبة",
        "condition": "الشروط والاستثناءات", "unknown_warning": (
            "غياب شرط في البيانات لا يعني الإعفاء منه."
        ),
        "license": "TravelRequirements.info · AXG Sp. z o.o. · CC BY 4.0 · ترجمة وتهيئة",
        "purpose_tourism": "السياحة", "purpose_business": "الأعمال",
        "purpose_transit": "العبور", "filter": "تصفية",
        "more_results": "الصفحة", "no_items": "لا توجد نتائج لهذه الفئة.",
        "search_results": "نتائج البحث", "unknown": "غير معروف",
    },
}

# Dates are *always* upstream publication and source-verification dates.
# Local download/synchronization times must not appear as legal verification.
LANG["fa"].update({
    "date_title": "تاریخ و اعتبار اطلاعات",
    "verified_date": "آخرین تأیید منبع مقررات",
    "changed_date": "آخرین تغییر ثبت‌شده در منبع",
    "updated_date": "آخرین به‌روزرسانی فایل مقصد",
    "full_review_date": "آخرین بازبینی کامل اطلاعات مقصد",
    "no_expiry": "تاریخ پایان اعتبار قانونی در منبع مشخص نشده است.",
    "date_notice": "این تاریخ‌ها تاریخ بررسی/انتشار اطلاعات هستند، نه تضمین اعتبار قانون تا آن روز.",
    "source_link": "مشاهده منبع مقررات",
    "original_data": "فایل اصلی اطلاعات مقصد (JSON)",
    "publisher": "دیتاست TravelRequirements.info",
    "license_link": "مجوز CC BY 4.0",
    "source_unavailable": "منبع در آخرین تلاش بررسی، قابل دسترسی یا تأیید نبوده است.",
    "conditional_notice": "استثناها ممکن است فقط شامل برخی تابعیت‌ها شوند.",
    "read_more": "مشاهده تمام جزئیات و منابع از دکمه‌های زیر",
    "visa_kind": "روش درخواست",
    "days": "روز",
    "source_label": "مرجع",
    "archived_copy": "نسخه آرشیوی",
    "not_checked": "تاریخ تأیید اعلام نشده",
    "documents_label": "مدارک درخواست",
    "unverified_field": "الزام یا معافیت این مورد در منبع تأیید نشده است.",
    "applicability": "دامنه اعتبار: ",
    "general_faq": "پرسش‌ها عمومی و ممکن است مربوط به پاسپورت دیگری باشند.",
    "processing_unit_minutes": "دقیقه",
    "processing_unit_days": "روز",
})
LANG["en"].update({
    "date_title": "Source dates & validity",
    "verified_date": "Source last verified",
    "changed_date": "Last source-recorded change",
    "updated_date": "Destination dataset last updated",
    "full_review_date": "Destination last fully reviewed",
    "no_expiry": "The source does not provide a legal expiry date for this requirement.",
    "date_notice": (
        "Verification and publication dates do not guarantee validity through that date."
    ),
    "source_link": "View entry-regulation source",
    "original_data": "Original destination JSON",
    "publisher": "TravelRequirements.info dataset",
    "license_link": "CC BY 4.0 license",
    "source_unavailable": "The source was inaccessible or unverifiable during its latest check.",
    "conditional_notice": "These exceptions may apply only to certain nationalities.",
    "read_more": "Open the detail and source tabs below",
    "visa_kind": "Application method",
    "days": "days",
    "source_label": "Reference",
    "archived_copy": "Archived source",
    "not_checked": "Verification date not provided",
    "documents_label": "Application documents",
    "unverified_field": "This obligation or exemption was not verified by the source.",
    "applicability": "Applicability: ",
    "general_faq": "General FAQs may describe passports other than yours.",
    "processing_unit_minutes": "minutes",
    "processing_unit_days": "days",
})
LANG["ar"].update({
    "date_title": "تواريخ المصدر وصلاحية المعلومات",
    "verified_date": "آخر تحقق من المصدر",
    "changed_date": "آخر تغيير مسجل في المصدر",
    "updated_date": "آخر تحديث لبيانات الوجهة",
    "full_review_date": "آخر مراجعة شاملة للوجهة",
    "no_expiry": "لم يحدد المصدر تاريخ انتهاء قانونياً لهذه المتطلبات.",
    "date_notice": "تواريخ المراجعة والنشر ليست ضماناً لاستمرار سريان القانون.",
    "source_link": "فتح مصدر شروط الدخول",
    "original_data": "ملف بيانات الوجهة الأصلي (JSON)",
    "publisher": "بيانات TravelRequirements.info",
    "license_link": "ترخيص CC BY 4.0",
    "source_unavailable": "تعذر الوصول إلى المصدر أو التحقق منه عند آخر فحص.",
    "conditional_notice": "قد تنطبق هذه الاستثناءات على جنسيات محددة فقط.",
    "read_more": "افتح أقسام التفاصيل والمصادر أدناه",
    "visa_kind": "طريقة التقديم",
    "days": "يوم",
    "source_label": "المصدر",
    "archived_copy": "نسخة مؤرشفة",
    "not_checked": "تاريخ التحقق غير متوفر",
    "documents_label": "وثائق الطلب",
    "unverified_field": "لم يثبت المصدر وجود هذا الشرط أو الإعفاء منه.",
    "applicability": "نطاق التطبيق: ",
    "general_faq": "قد تتعلق الأسئلة العامة بجوازات سفر أخرى.",
    "processing_unit_minutes": "دقائق",
    "processing_unit_days": "أيام",
})


COUNTRY_LABELS = {
    "fa": {
        "AF": "افغانستان", "IR": "ایران", "TR": "ترکیه", "AE": "امارات",
        "DE": "آلمان", "FR": "فرانسه", "GB": "بریتانیا", "US": "آمریکا",
        "CA": "کانادا", "AU": "استرالیا", "IN": "هند", "PK": "پاکستان",
        "IQ": "عراق", "SA": "عربستان", "QA": "قطر", "OM": "عمان",
        "AZ": "آذربایجان", "AM": "ارمنستان", "GE": "گرجستان",
        "RU": "روسیه", "CN": "چین", "JP": "ژاپن", "IT": "ایتالیا",
        "ES": "اسپانیا", "NL": "هلند", "SE": "سوئد", "CH": "سوئیس",
        "AT": "اتریش", "GR": "یونان", "MY": "مالزی", "TH": "تایلند",
        "ID": "اندونزی", "SG": "سنگاپور", "KR": "کره جنوبی", "UZ": "ازبکستان",
        "TJ": "تاجیکستان", "TM": "ترکمنستان", "KZ": "قزاقستان",
        "KG": "قرقیزستان", "BR": "برزیل", "EG": "مصر", "LB": "لبنان",
        "KW": "کویت", "BH": "بحرین", "SY": "سوریه", "JO": "اردن",
    },
    "ar": {
        "AF": "أفغانستان", "IR": "إيران", "TR": "تركيا", "AE": "الإمارات",
        "DE": "ألمانيا", "FR": "فرنسا", "GB": "بريطانيا", "US": "الولايات المتحدة",
        "CA": "كندا", "IN": "الهند", "PK": "باكستان", "IQ": "العراق",
        "SA": "السعودية", "QA": "قطر", "OM": "عمان", "AZ": "أذربيجان",
        "AM": "أرمينيا", "GE": "جورجيا", "RU": "روسيا", "CN": "الصين",
        "JP": "اليابان", "EG": "مصر", "KW": "الكويت", "BH": "البحرين",
    },
}

STATUS_NAMES = {
    "visa-free": ("بدون ویزا", "Visa-free", "بدون تأشيرة"),
    "freedom-of-movement": ("آزادی تردد", "Freedom of movement", "حرية التنقل"),
    "evisa": ("ویزای الکترونیکی", "eVisa", "تأشيرة إلكترونية"),
    "e-visa": ("ویزای الکترونیکی", "eVisa", "تأشيرة إلكترونية"),
    "visa-on-arrival": ("ویزای فرودگاهی", "Visa on arrival", "تأشيرة عند الوصول"),
    "eta": ("مجوز سفر الکترونیکی", "Electronic travel authorisation", "تصريح سفر إلكتروني"),
    "embassy-visa": ("ویزای سفارتی", "Embassy visa", "تأشيرة سفارة"),
    "visa-required": ("نیازمند ویزا", "Visa required", "التأشيرة مطلوبة"),
    "refused": ("ورود محدود یا ممنوع", "Admission restricted", "الدخول مقيّد"),
    "unknown": ("اطلاعات نامشخص", "Unknown", "غير معروف"),
}
LANG_INDEX = {"fa": 0, "en": 1, "ar": 2}
MAIN_SOURCE = "https://travelrequirements.info/data/"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


def tr(language: str, key: str) -> str:
    return LANG.get(language, LANG["en"]).get(key, LANG["en"].get(key, key))


def country_label(code: str, name: str, language: str) -> str:
    code = code.upper()
    override = COUNTRY_LABELS.get(language, {}).get(code)
    if override:
        return override
    if language in {"fa", "ar", "en"}:
        localized = Locale.parse(language).territories.get(code)
        if localized:
            return str(localized)
    return name


def status_label(value: str, language: str) -> str:
    return STATUS_NAMES.get(value, STATUS_NAMES["unknown"])[LANG_INDEX.get(language, 1)]


def safe_href(url: object) -> str | None:
    """HTML-escaped HTTPS URL retained for existing render integrations."""
    safe = safe_source_url(url)
    return escape(safe, quote=True) if safe else None


def external_link(url: object, label: str) -> str:
    return link_html(url, label)


def _provider_links(provenance: VisaProvenance, language: str) -> str:
    links = [
        external_link(provenance.source_url, tr(language, "source_link")),
        external_link(provenance.destination_json_url, tr(language, "original_data")),
    ]
    return " · ".join(item for item in links if item)


def _attribution(language: str) -> str:
    return (
        external_link(MAIN_SOURCE, tr(language, "publisher"))
        + " · "
        + external_link(LICENSE_URL, tr(language, "license_link"))
    )


def _source_dates(
    provenance: VisaProvenance, language: str, *, full: bool = False
) -> list[str]:
    """Clearly distinguish source verification, source changes, and dataset publication."""
    missing = tr(language, "not_known")
    lines = [
        f"• <b>{escape(tr(language, 'verified_date'))}:</b> "
        f"{escape(provenance.source_verified_on or missing)}",
    ]
    if provenance.source_changed_on:
        lines.append(
            f"• <b>{escape(tr(language, 'changed_date'))}:</b> "
            f"{escape(provenance.source_changed_on)}"
        )
    lines.append(
        f"• <b>{escape(tr(language, 'updated_date'))}:</b> "
        f"{escape(provenance.destination_updated_on or missing)}"
    )
    if full and provenance.last_full_review_on:
        lines.append(
            f"• <b>{escape(tr(language, 'full_review_date'))}:</b> "
            f"{escape(provenance.last_full_review_on)}"
        )
    if provenance.verified_is_stale:
        lines.append("⚠️ " + escape(
            "Source verification is over 30 days old"
            if language == "en" else
            "بیش از ۳۰ روز از آخرین بررسی منبع گذشته است"
            if language == "fa" else
            "مر أكثر من ٣٠ يوماً على آخر تحقق من المصدر"
        ))
    if provenance.source_unverifiable:
        lines.append("⚠️ " + escape(tr(language, "source_unavailable")))
    return lines


def _limited_lines(lines: list[str], *, max_chars: int = 3900) -> str:
    """Keep HTML tags intact. Truncate only at complete, already escaped lines."""
    selected: list[str] = []
    length = 0
    for line in lines:
        if length + len(line) + 1 > max_chars - 50:
            selected.append("…")
            break
        selected.append(line)
        length += len(line) + 1
    return "\n".join(selected)


def render_overview(
    detail: VisaDetail,
    language: str,
    *,
    passport_name: str = "",
    residence: str | None = None,
    purpose: str = "tourism",
) -> str:
    """Compact, professional Telegram HTML with hyperlink citations and upstream dates."""
    rule = detail.rule
    provenance = visa_provenance(detail)
    name = country_label(rule.destination, rule.country_name, language)
    passenger = country_label(rule.passport, passport_name or rule.passport, language)
    icons = {
        "visa-free": "✅", "freedom-of-movement": "✅",
        "evisa": "🟡", "e-visa": "🟡", "eta": "🟡",
        "visa-on-arrival": "🟡", "embassy-visa": "🔴",
        "visa-required": "🔴", "refused": "⛔",
    }
    stay = (
        f"{rule.stay_days} {tr(language, 'days')}"
        if rule.stay_days is not None else tr(language, "not_known")
    )
    purpose_label = tr(language, "purpose_" + purpose)
    lines = [
        f"<b>{escape(tr(language, 'title'))}</b>",
        f"{escape(passenger)} ({escape(rule.passport)}) → "
        f"<b>{escape(name)}</b> ({escape(rule.destination)})",
        "━━━━━━━━━━━━━━━━",
        f"{icons.get(rule.status, 'ℹ️')} <b>{escape(tr(language, 'status'))}:</b> "
        f"{escape(status_label(rule.status, language))}",
        f"⏳ <b>{escape(tr(language, 'stay'))}:</b> {escape(stay)}",
        f"🎯 <b>{escape(tr(language, 'purpose'))}:</b> {escape(purpose_label)}",
    ]
    if residence:
        lines.append(
            f"🏠 <b>{escape(tr(language, 'residence'))}:</b> "
            f"<code>{escape(residence)}</code>"
        )
    if rule.notes:
        lines.extend(["", f"<b>{escape(tr(language, 'more'))}</b>"])
        lines.append(escape(rule.notes[:1100]))
    waivers = detail.destination_data.get("visaPolicy", {}).get("conditionalWaivers") or []
    if waivers and rule.status not in {"visa-free", "freedom-of-movement"}:
        lines.extend(["", f"<b>{escape(tr(language, 'condition'))}</b>"])
        for waiver in waivers[:2]:
            if isinstance(waiver, dict) and waiver.get("text"):
                lines.append("• " + escape(str(waiver["text"])[:350]))
        lines.append("<i>" + escape(tr(language, "conditional_notice")) + "</i>")
    lines.extend(["", f"<b>🗓 {escape(tr(language, 'date_title'))}</b>"])
    lines.extend(_source_dates(provenance, language))
    lines.append(
        "🔎 " + escape(
            tr(language, "row") if provenance.source_level == "row"
            else tr(language, "policy")
        )
    )
    lines.append(_provider_links(provenance, language))
    lines.extend([
        "",
        "⚠️ " + escape(tr(language, "caution")),
    ])
    if residence or purpose != "tourism":
        lines.append("⚠️ " + escape(tr(language, "unmodeled")))
    lines.extend([
        "<i>" + escape(tr(language, "date_notice")) + "</i>",
        "",
        _attribution(language),
    ])
    return _limited_lines(lines)


_ENTRY_LABELS = {
    "passportValidity": ("اعتبار گذرنامه", "Passport validity", "صلاحية جواز السفر"),
    "vaccinations": ("واکسیناسیون", "Vaccinations", "التطعيمات"),
    "travelInsurance": ("بیمه مسافرتی", "Travel insurance", "تأمين السفر"),
    "onwardTicket": ("بلیط برگشت / ادامه مسیر", "Return / onward ticket", "تذكرة العودة"),
    "proofOfFunds": ("تمکن مالی", "Proof of funds", "إثبات الأموال"),
    "declarations": ("اظهارنامه‌های ورود", "Entry declarations", "إقرارات الدخول"),
    "customs": ("قوانین گمرکی", "Customs", "الجمارك"),
}
_FACT_LABELS = {
    "currency": ("واحد پول", "Currency", "العملة"),
    "languages": ("زبان‌ها", "Languages", "اللغات"),
    "timezone": ("منطقه زمانی", "Time zone", "المنطقة الزمنية"),
    "payments": ("پرداخت و کارت بانکی", "Payments", "طرق الدفع"),
    "safety": ("ایمنی و هشدارهای سفر", "Travel safety", "السلامة"),
    "plugs": ("برق و پریز", "Plugs and electricity", "الكهرباء والمقابس"),
    "emergency": ("شماره اضطراری", "Emergency numbers", "أرقام الطوارئ"),
    "drivingSide": ("سمت رانندگی", "Driving side", "جهة القيادة"),
    "driving": ("رانندگی و گواهینامه", "Driving", "القيادة"),
    "tapWaterSafe": ("آب آشامیدنی", "Drinking water", "مياه الشرب"),
    "bestTimeToVisit": ("زمان مناسب سفر", "Best time to visit", "أفضل وقت للزيارة"),
}
_METHOD_NAMES = {
    "evisa": ("ویزای الکترونیکی", "eVisa", "تأشيرة إلكترونية"),
    "embassy": ("ویزای سفارتی", "Embassy visa", "تأشيرة سفارة"),
    "on-arrival": ("ویزای هنگام ورود", "On-arrival visa", "تأشيرة عند الوصول"),
    "visa-free": ("معاف از ویزا", "Visa-free", "بدون تأشيرة"),
}


def _label(labels: dict, key: str, language: str) -> str:
    names = labels.get(key)
    return names[LANG_INDEX.get(language, 1)] if names else key


def _value_text(value: object, language: str = "en", *, limit: int = 650) -> str:
    """Format nested source fields intelligibly without dumping machine keys."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return ("بله" if value else "خیر") if language == "fa" else (
            "نعم" if value else "لا"
        ) if language == "ar" else ("Yes" if value else "No")
    if isinstance(value, dict):
        if value.get("text"):
            return str(value["text"])[:limit]
        if value.get("amount") is not None:
            return (
                f"{value['amount']} {value.get('currency') or ''}"
            ).strip()[:limit]
        if value.get("name") and value.get("code"):
            return f"{value['name']} ({value['code']})"[:limit]
        if isinstance(value.get("types"), list):
            types = ", ".join(str(item) for item in value["types"][:8])
            voltage = value.get("voltage")
            frequency = value.get("frequencyHz")
            additional = []
            if voltage is not None:
                additional.append(f"{voltage}V")
            if frequency is not None:
                additional.append(f"{frequency}Hz")
            return " · ".join([types, *additional])[:limit]
        fragments = [
            f"{key.replace('_', ' ')}: {_value_text(val, language, limit=140)}"
            for key, val in value.items()
            if key not in {"source", "sources", "unverifiable"} and val is not None
        ]
        return "؛ ".join(fragments)[:limit]
    if isinstance(value, list):
        return "، ".join(_value_text(item, language, limit=140) for item in value[:12])[:limit]
    return str(value)[:limit]


def _source_line(item: object, language: str) -> str:
    """Source link and its own review/change dates; never use bot import dates."""
    if not isinstance(item, dict):
        return ""
    source = item.get("source") if isinstance(item.get("source"), dict) else item
    if not isinstance(source, dict):
        return ""
    name = str(source.get("name") or tr(language, "source_label"))[:95]
    href = external_link(source.get("url"), name)
    if not href:
        return ""
    parts = ["🔗 " + href]
    verified = source_date(source.get("lastVerified"))
    changed = source_date(source.get("lastChanged"))
    if verified:
        parts.append(f"{escape(tr(language, 'verified_date'))}: {verified}")
    if changed:
        parts.append(f"{escape(tr(language, 'changed_date'))}: {changed}")
    archive = external_link(source.get("archiveUrl"), tr(language, "archived_copy"))
    if archive:
        parts.append(archive)
    return " · ".join(parts)


def _lines_for_list(
    items: object, language: str = "en", *, max_items: int = 15, limit: int = 500
) -> list[str]:
    if not isinstance(items, list):
        return []
    results: list[str] = []
    for item in items[:max_items]:
        if isinstance(item, dict):
            value = item.get("text") or item.get("name") or item.get("question")
            if value:
                results.append("• " + escape(str(value)[:limit]))
                source = _source_line(item, language)
                if source:
                    results.append(source)
        else:
            results.append("• " + escape(str(item)[:limit]))
    if len(items) > max_items:
        results.append(f"… (+{len(items) - max_items})")
    return results


def _processing_text(value: object, language: str) -> str:
    if not isinstance(value, dict):
        return _value_text(value, language)
    minimum = value.get("minDays")
    maximum = value.get("maxDays")
    if minimum is None and maximum is None:
        return tr(language, "not_known")
    unit = value.get("unit")
    localized_unit = (
        tr(language, "processing_unit_minutes")
        if unit == "minutes" else tr(language, "processing_unit_days")
    )
    duration = (
        str(minimum) if minimum == maximum else
        f"{minimum or 0}–{maximum}" if maximum is not None else str(minimum)
    )
    return f"{duration} {localized_unit}"


def _section_header(language: str, section: str) -> list[str]:
    icons = {
        "types": "🛂", "entry": "📋", "facts": "🌍",
        "tips": "⚠️", "faq": "❔", "sources": "🔎", "transit": "🛫",
    }
    return [f"<b>{icons.get(section, '•')} {escape(tr(language, section))}</b>",
            "━━━━━━━━━━━━━━━━", ""]


def _section_footer(provenance: VisaProvenance, language: str) -> list[str]:
    return [
        "",
        "──────────",
        f"🗓 {escape(tr(language, 'updated_date'))}: "
        f"{escape(provenance.destination_updated_on or tr(language, 'not_known'))}",
        _provider_links(provenance, language),
        _attribution(language),
    ]


def render_section(detail: VisaDetail, language: str, section: str) -> str:
    """Source-linked Telegram detail tabs with coherent dates and readable formatting."""
    document = detail.destination_data
    requirements = document.get("entryRequirements") or {}
    facts = document.get("countryFacts") or {}
    provenance = visa_provenance(detail)
    lines = _section_header(language, section)

    if section == "types":
        if not detail.visa_types:
            lines.append(escape(tr(language, "not_known")))
        for visa in detail.visa_types[:10]:
            title = str(visa.get("name") or visa.get("id") or "Visa")
            lines.append(f"<b>🛂 {escape(title[:150])}</b>")
            method = visa.get("method")
            if method:
                lines.append(
                    f"• <b>{escape(tr(language, 'visa_kind'))}:</b> "
                    f"{escape(_label(_METHOD_NAMES, str(method), language))}"
                )
            fee = visa.get("fee")
            if fee is not None:
                lines.append(
                    f"• <b>{escape(tr(language, 'fee'))}:</b> "
                    f"{escape(_value_text(fee, language, limit=200))}"
                )
                if isinstance(fee, dict) and fee.get("notes"):
                    lines.append(escape(str(fee["notes"])[:520]))
            processing = visa.get("processing")
            if processing is not None:
                lines.append(
                    f"• <b>{escape(tr(language, 'processing'))}:</b> "
                    f"{escape(_processing_text(processing, language))}"
                )
            for key, title_key in (
                ("stayDays", "stay"), ("validityDays", "validity"),
                ("entries", "entries"),
            ):
                if visa.get(key) is not None:
                    value = _value_text(visa[key], language)
                    if key in {"stayDays", "validityDays"}:
                        value += " " + tr(language, "days")
                    lines.append(f"• <b>{escape(tr(language, title_key))}:</b> {escape(value)}")
            window = visa.get("applyWindow")
            if isinstance(window, dict) and window.get("text"):
                lines.append(escape(str(window["text"])[:520]))
                src = _source_line(window, language)
                if src:
                    lines.append(src)
            application = external_link(visa.get("applyUrl"), tr(language, "apply"))
            if application:
                lines.append("🔗 " + application)
            docs = visa.get("documents") or {}
            if isinstance(docs, dict):
                items = docs.get("items")
                if isinstance(items, list) and items:
                    lines.append(f"<b>📑 {escape(tr(language, 'docs'))}</b>")
                    for item in items[:16]:
                        if not isinstance(item, dict):
                            lines.append("• " + escape(str(item)[:200]))
                            continue
                        name = str(item.get("name") or item.get("id") or "Document")
                        optional = " (optional)" if item.get("required") is False else ""
                        spec = str(item.get("details") or "")
                        lines.append("• <b>" + escape(name[:120] + optional) + "</b>")
                        if spec:
                            lines.append("  " + escape(spec[:350]))
                doc_source = _source_line(docs, language)
                if doc_source:
                    lines.append(doc_source)
            visa_source = _source_line(visa, language)
            if visa_source:
                lines.append(visa_source)
            lines.append("──────────")
    elif section == "entry":
        for field in _ENTRY_LABELS:
            value = requirements.get(field)
            if value is None or value == []:
                continue
            lines.append(f"<b>• {escape(_label(_ENTRY_LABELS, field, language))}</b>")
            if isinstance(value, dict):
                explanation = value.get("text") or value.get("rule")
                if explanation:
                    lines.append(escape(str(explanation)[:650]))
                else:
                    lines.append(escape(tr(language, "unverified_field")))
                source = _source_line(value, language)
                if source:
                    lines.append(source)
            elif isinstance(value, list):
                lines.extend(_lines_for_list(value, language, max_items=8))
            else:
                lines.append(escape(_value_text(value, language)))
            lines.append("")
        lines.append("<i>" + escape(tr(language, "unknown_warning")) + "</i>")
    elif section == "facts":
        overview = document.get("summary")
        if overview:
            lines.extend([escape(str(overview)[:700]), ""])
        for key in _FACT_LABELS:
            value = facts.get(key)
            if value is None:
                continue
            title = _label(_FACT_LABELS, key, language)
            if key == "tapWaterSafe":
                # The raw boolean does not support a universal sanitary claim.
                text = tr(language, "unverified_field")
            else:
                text = _value_text(value, language)
            lines.append(f"<b>• {escape(title)}:</b> {escape(text[:650])}")
            if isinstance(value, dict):
                source = _source_line(value, language)
                if source:
                    lines.append(source)
    elif section == "tips":
        tips = document.get("tips") or []
        lines.extend(_lines_for_list(tips, language, max_items=16, limit=600))
    elif section == "faq":
        for item in (document.get("faq") or [])[:16]:
            if isinstance(item, dict):
                question = item.get("question")
                answer = item.get("answer")
                if question:
                    lines.append(f"<b>❓ {escape(str(question)[:250])}</b>")
                if answer:
                    lines.extend([escape(str(answer)[:600]), ""])
        lines.append("⚠️ " + escape(tr(language, "general_faq")))
    elif section == "sources":
        lines.extend(_source_dates(provenance, language, full=True))
        lines.append("<i>" + escape(tr(language, "no_expiry")) + "</i>")
        lines.append("<i>" + escape(tr(language, "date_notice")) + "</i>")
        lines.append(
            "🔎 " + escape(
                tr(language, "row") if provenance.source_level == "row"
                else tr(language, "policy")
            )
        )
        sources = [detail.record.get("source")]
        policy = document.get("visaPolicy") or {}
        sources.append(policy.get("defaultSource"))
        sources.extend((document.get("meta") or {}).get("primarySources") or [])
        for section_value in (document.get("entryRequirements") or {}).values():
            if isinstance(section_value, dict):
                sources.append(section_value.get("source"))
        for visa in detail.visa_types:
            sources.append(visa.get("source"))
            docs = visa.get("documents")
            if isinstance(docs, dict):
                sources.append(docs.get("source"))
        seen_urls: set[str] = set()
        for source in sources:
            if not isinstance(source, dict):
                continue
            href = safe_source_url(source.get("url"))
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)
            line = _source_line(source, language)
            if line:
                lines.append(line)
            if len(seen_urls) >= 14:
                break
    elif section == "transit":
        supplied = False
        for key in ("transit", "entryModes", "levies"):
            item = document.get(key)
            if not item:
                continue
            supplied = True
            lines.append("<b>" + escape(str(key)) + "</b>")
            if isinstance(item, dict):
                for label, value in list(item.items())[:12]:
                    if label == "source":
                        line = _source_line(value, language)
                        if line:
                            lines.append(line)
                    else:
                        lines.append(
                            "• " + escape(label.replace("_", " ").capitalize()) + ": "
                            + escape(_value_text(value, language, limit=450))
                        )
            else:
                lines.append(escape(_value_text(item, language)))
        if not supplied:
            lines.append(escape(tr(language, "not_known")))
        lines.append("⚠️ " + escape(tr(language, "caution")))
    else:
        return escape(tr(language, "unknown"))

    if len(lines) <= 3:
        lines.append(escape(tr(language, "not_known")))
    # Reserve room for citations so long tips/FAQs never hide the hyperlinks.
    footer = _section_footer(provenance, language)
    footer_text = "\n".join(footer)
    body = _limited_lines(lines, max_chars=3900 - len(footer_text) - 2)
    return body + "\n" + footer_text


def render_rich_report(detail: VisaDetail, language: str) -> dict:
    """Produce valid, balanced native rich blocks with genuine source hyperlinks."""
    rule = detail.rule
    provenance = visa_provenance(detail)
    passport = country_label(rule.passport, rule.passport, language)
    destination = country_label(rule.destination, rule.country_name, language)
    stay = (
        f"{rule.stay_days} {tr(language, 'days')}"
        if rule.stay_days is not None else tr(language, "not_known")
    )
    head = (
        f"<h3>{escape(tr(language, 'title'))}</h3>"
        f"<p>{escape(passport)} ({escape(rule.passport)}) → "
        f"<b>{escape(destination)}</b> ({escape(rule.destination)})</p>"
    )
    rows = [
        (tr(language, "status"), status_label(rule.status, language)),
        (tr(language, "stay"), stay),
        (tr(language, "verified_date"),
         provenance.source_verified_on or tr(language, "not_known")),
        (tr(language, "updated_date"),
         provenance.destination_updated_on or tr(language, "not_known")),
    ]
    if provenance.source_changed_on:
        rows.append((tr(language, "changed_date"), provenance.source_changed_on))
    table = "<table bordered striped compact>" + "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in rows
    ) + "</table>"
    intro = "<p>" + _provider_links(provenance, language) + "</p>"
    intro += "<p><i>" + escape(tr(language, "date_notice")) + "</i></p>"
    sections: list[str] = []
    for key in ("types", "entry", "transit", "facts", "tips", "faq", "sources"):
        content = render_section(detail, language, key)
        content_lines = content.split("\n")[3:]
        paragraphs = "".join(
            f"<p>{line}</p>" for line in content_lines if line.strip()
        )
        sections.append(f"<h3>{escape(tr(language, key))}</h3>{paragraphs}")
    footer = (
        "<p>⚠️ " + escape(tr(language, "caution")) + "</p>"
        + "<p>" + _attribution(language) + "</p>"
    )
    blocks = [head, table, intro]
    current_length = len(head + table + intro + footer)
    for part in sections:
        if current_length + len(part) > 28_000:
            break
        blocks.append(part)
        current_length += len(part)
    blocks.append(footer)
    return {"html": "".join(blocks), "is_rtl": language in {"fa", "ar"}}


def country_keyboard(
    countries: list[Country],
    language: str,
    *,
    purpose: str,
    page: int = 0,
    query: str | None = None,
) -> InlineKeyboardMarkup:
    """Page through all passports/destinations; no 64-byte callback overflow."""
    page_size = 14
    max_page = max(0, (len(countries) - 1) // page_size)
    page = min(max(0, page), max_page)
    start = page * page_size
    rows = []
    for i in range(start, min(start + page_size, len(countries)), 2):
        rows.append([
            InlineKeyboardButton(
                f"{country_label(c.code, c.name, language)} · {c.code}",
                callback_data=f"visa:{purpose}:{c.code}",
            )
            for c in countries[i : min(i + 2, len(countries))]
        ])
    if query is None:
        navigation = []
        if page:
            navigation.append(
                InlineKeyboardButton("◀", callback_data=f"visa:pick:{purpose}:{page - 1}")
            )
        if page < max_page:
            navigation.append(
                InlineKeyboardButton("▶", callback_data=f"visa:pick:{purpose}:{page + 1}")
            )
        if navigation:
            rows.append(navigation)
    rows.append([
        InlineKeyboardButton(tr(language, "search"), callback_data=f"visa:search:{purpose}")
    ])
    rows.append([InlineKeyboardButton(tr(language, "back"), callback_data="visa:home")])
    return InlineKeyboardMarkup(rows)


def home_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(language, "passports"), callback_data="visa:pick:p:0")],
        [InlineKeyboardButton(tr(language, "back"), callback_data="back")],
    ])


def passport_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(language, "choose_destination"), callback_data="visa:pick:d:0")],
        [InlineKeyboardButton(tr(language, "list"), callback_data="visa:groups")],
        [InlineKeyboardButton(tr(language, "passports"), callback_data="visa:pick:p:0")],
        [InlineKeyboardButton(tr(language, "back"), callback_data="visa:home")],
    ])


def detail_keyboard(
    language: str, detail: VisaDetail | None = None
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(tr(language, "details"), callback_data="visa:rich")],
        [InlineKeyboardButton(tr(language, "types"), callback_data="visa:section:types"),
         InlineKeyboardButton(tr(language, "entry"), callback_data="visa:section:entry")],
        [InlineKeyboardButton(tr(language, "transit"), callback_data="visa:section:transit"),
         InlineKeyboardButton(tr(language, "facts"), callback_data="visa:section:facts")],
        [InlineKeyboardButton(tr(language, "tips"), callback_data="visa:section:tips"),
         InlineKeyboardButton(tr(language, "faq"), callback_data="visa:section:faq")],
        [InlineKeyboardButton(tr(language, "sources"), callback_data="visa:section:sources")],
        [InlineKeyboardButton(tr(language, "residence_button"), callback_data="visa:pick:r:0"),
         InlineKeyboardButton(tr(language, "clear_residence"), callback_data="visa:r:clear")],
        [InlineKeyboardButton(tr(language, "purpose_tourism"), callback_data="visa:pur:tourism"),
         InlineKeyboardButton(tr(language, "purpose_business"), callback_data="visa:pur:business"),
         InlineKeyboardButton(tr(language, "purpose_transit"), callback_data="visa:pur:transit")],
        [InlineKeyboardButton(tr(language, "another"), callback_data="visa:pick:d:0")],
        [InlineKeyboardButton(tr(language, "list"), callback_data="visa:groups")],
        [InlineKeyboardButton(tr(language, "passports"), callback_data="visa:pick:p:0")],
    ]
    if detail is not None:
        provenance = visa_provenance(detail)
        source_url = safe_source_url(provenance.source_url)
        original_url = safe_source_url(provenance.destination_json_url)
        reference_buttons = []
        if source_url:
            reference_buttons.append(
                InlineKeyboardButton(tr(language, "source_link"), url=source_url)
            )
        if original_url:
            reference_buttons.append(
                InlineKeyboardButton(tr(language, "original_data"), url=original_url)
            )
        if reference_buttons:
            rows.insert(1, reference_buttons)
    return InlineKeyboardMarkup(rows)


def section_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(language, "summary"), callback_data="visa:result")],
        [InlineKeyboardButton(tr(language, "another"), callback_data="visa:pick:d:0")],
    ])


def groups_keyboard(
    language: str, counts: dict[str, int] | None = None
) -> InlineKeyboardMarkup:
    counts = counts or {}
    rows = []
    for group in ("all", "free", "evisa", "arrival", "required", "other"):
        statuses = STATUS_GROUPS.get(group, tuple(counts))
        count = sum(counts.get(item, 0) for item in statuses)
        label = tr(language, group) + (f" · {count}" if counts else "")
        rows.append([InlineKeyboardButton(label, callback_data=f"visa:list:{group}:0")])
    rows.append([InlineKeyboardButton(tr(language, "back"), callback_data="visa:pick:d:0")])
    return InlineKeyboardMarkup(rows)


def listing_keyboard(
    language: str, rules: list[VisaRule], group: str, page: int, total: int
) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(rules), 2):
        rows.append([
            InlineKeyboardButton(
                country_label(rule.destination, rule.country_name, language),
                callback_data=f"visa:d:{rule.destination}",
            )
            for rule in rules[i : i + 2]
        ])
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton("◀", callback_data=f"visa:list:{group}:{page - 1}"))
    if (page + 1) * 12 < total:
        navigation.append(InlineKeyboardButton("▶", callback_data=f"visa:list:{group}:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(tr(language, "filter"), callback_data="visa:groups")])
    rows.append([InlineKeyboardButton(tr(language, "back"), callback_data="visa:home")])
    return InlineKeyboardMarkup(rows)
