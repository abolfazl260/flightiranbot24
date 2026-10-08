"""Localized, safely escaped Telegram visa cards and native rich reports."""

from __future__ import annotations

import re
from html import escape, unescape
from urllib.parse import urlparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.visa.catalog import Country, VisaDetail, VisaRule

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
        "license": "TravelRequirements.info · CC BY 4.0",
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
        "unmodeled": "This dataset does not fully calculate residence or special-purpose eligibility.",
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
        "license": "TravelRequirements.info · CC BY 4.0",
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
        "license": "TravelRequirements.info · CC BY 4.0",
        "purpose_tourism": "السياحة", "purpose_business": "الأعمال",
        "purpose_transit": "العبور", "filter": "تصفية",
        "more_results": "الصفحة", "no_items": "لا توجد نتائج لهذه الفئة.",
        "search_results": "نتائج البحث", "unknown": "غير معروف",
    },
}

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
    return COUNTRY_LABELS.get(language, {}).get(code.upper(), name)


def status_label(value: str, language: str) -> str:
    return STATUS_NAMES.get(value, STATUS_NAMES["unknown"])[LANG_INDEX.get(language, 1)]


def safe_href(url: object) -> str | None:
    if not isinstance(url, str):
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    if len(url) > 900:
        return None
    return escape(url, quote=True)


def external_link(url: object, label: str) -> str:
    clean = safe_href(url)
    return f'<a href="{clean}">{escape(label)}</a>' if clean else ""


def render_overview(
    detail: VisaDetail,
    language: str,
    *,
    passport_name: str = "",
    residence: str | None = None,
    purpose: str = "tourism",
) -> str:
    rule = detail.rule
    name = country_label(rule.destination, rule.country_name, language)
    passenger = country_label(rule.passport, passport_name or rule.passport, language)
    source = external_link(rule.source_url, tr(language, "source"))
    lines = [
        f"<b>{tr(language, 'title')}</b>",
        "",
        f"🛂 <b>{tr(language, 'passport')}:</b> {escape(passenger)} "
        f"<code>{escape(rule.passport)}</code>",
        f"🌍 <b>{tr(language, 'destination')}:</b> {escape(name)} "
        f"<code>{escape(rule.destination)}</code>",
        f"📌 <b>{tr(language, 'status')}:</b> "
        f"{escape(status_label(rule.status, language))}",
        f"🕓 <b>{tr(language, 'stay')}:</b> "
        f"{rule.stay_days if rule.stay_days is not None else tr(language, 'not_known')}"
        + (" days" if rule.stay_days is not None else ""),
        f"🎯 <b>{tr(language, 'purpose')}:</b> {tr(language, 'purpose_' + purpose)}",
    ]
    if residence:
        lines.append(f"🏠 <b>{tr(language, 'residence')}:</b> <code>{escape(residence)}</code>")
    if rule.notes:
        lines.extend(["", f"ℹ️ {escape(rule.notes[:1250])}"])
    waivers = detail.destination_data.get("visaPolicy", {}).get("conditionalWaivers") or []
    if waivers and rule.status not in {"visa-free", "freedom-of-movement"}:
        lines.extend(["", f"<b>{tr(language, 'condition')}</b>"])
        for waiver in waivers[:3]:
            if isinstance(waiver, dict) and waiver.get("text"):
                lines.append("• " + escape(str(waiver["text"])[:450]))
    lines.extend([
        "",
        "🔎 " + (tr(language, "row") if rule.source_level == "row"
                  else tr(language, "policy")),
        f"🗓 {tr(language, 'checked')}: "
        f"{escape(rule.verified_on or tr(language, 'not_known'))}",
    ])
    if source:
        lines.append(source)
    lines.extend([
        "",
        f"⚠️ {escape(tr(language, 'caution'))}",
    ])
    if residence or purpose != "tourism":
        lines.append(f"⚠️ {escape(tr(language, 'unmodeled'))}")
    lines.append(external_link(MAIN_SOURCE, tr(language, "license")))
    return "\n".join(lines)[:3800]


def _value_text(value: object, *, limit: int = 650) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return ", ".join(
            f"{str(k)}: {_value_text(v, limit=140)}"
            for k, v in value.items()
            if k != "source" and v is not None
        )[:limit]
    if isinstance(value, list):
        return "; ".join(_value_text(x, limit=170) for x in value[:12])[:limit]
    return str(value)[:limit]


def _source_line(item: object, language: str) -> str:
    if not isinstance(item, dict):
        return ""
    source = item.get("source") if "source" in item else item
    if not isinstance(source, dict):
        return ""
    link = external_link(source.get("url"), str(source.get("name") or tr(language, "source")))
    checked = source.get("lastVerified")
    return ("🔗 " + link if link else "") + (
        " · " + escape(str(checked)) if checked else ""
    )


def _lines_for_list(items: object, *, max_items: int = 15, limit: int = 500) -> list[str]:
    if not isinstance(items, list):
        return []
    results: list[str] = []
    for item in items[:max_items]:
        if isinstance(item, dict):
            value = item.get("text") or item.get("name") or item.get("question")
            if value:
                results.append("• " + escape(str(value)[:limit]))
        else:
            results.append("• " + escape(str(item)[:limit]))
    if len(items) > max_items:
        results.append(f"… (+{len(items) - max_items})")
    return results


def render_section(detail: VisaDetail, language: str, section: str) -> str:
    """Source-aware, bounded HTML suitable for Telegram editMessageText."""
    doc = detail.destination_data
    requirements = doc.get("entryRequirements") or {}
    facts = doc.get("countryFacts") or {}
    lines = [f"<b>{escape(tr(language, section))}</b>", ""]
    if section == "types":
        if not detail.visa_types:
            lines.append(escape(tr(language, "not_known")))
        for visa in detail.visa_types[:10]:
            lines.append("🛂 <b>" + escape(str(visa.get("name") or visa.get("id"))) + "</b>")
            for key, label in (
                ("method", "Type"), ("fee", tr(language, "fee")),
                ("processing", tr(language, "processing")),
                ("stayDays", tr(language, "stay")),
                ("validityDays", tr(language, "validity")),
                ("entries", tr(language, "entries")),
            ):
                if visa.get(key) is not None:
                    lines.append(f"• {escape(label)}: {escape(_value_text(visa[key]))}")
            link = external_link(visa.get("applyUrl"), tr(language, "apply"))
            if link:
                lines.append(link)
            docs = visa.get("documents") or {}
            if isinstance(docs, dict):
                if docs.get("items"):
                    lines.append(f"<b>{tr(language, 'docs')}</b>")
                    lines.extend(_lines_for_list(docs["items"], max_items=12))
                src = _source_line(docs, language)
                if src:
                    lines.append(src)
            src = _source_line(visa, language)
            if src:
                lines.append(src)
            lines.append("")
    elif section == "entry":
        entries = (
            ("passportValidity", "Passport validity"),
            ("travelInsurance", "Travel insurance"),
            ("onwardTicket", "Return/onward ticket"),
            ("proofOfFunds", "Proof of funds"),
            ("vaccinations", "Vaccinations"),
            ("declarations", "Arrival declarations"),
            ("customs", "Customs and currency"),
        )
        for field, label in entries:
            val = requirements.get(field)
            if val is None or val == []:
                continue
            lines.append(f"• <b>{escape(label)}</b>")
            if isinstance(val, dict):
                # Never interpret 'required: false' as proven exemption.
                explanation = val.get("text") or val.get("rule") or (
                    _value_text(val) if "required" not in val else None
                )
                if explanation:
                    lines.append(escape(str(explanation)[:550]))
                else:
                    lines.append(escape(tr(language, "unknown_warning")))
                source = _source_line(val, language)
                if source:
                    lines.append(source)
            elif isinstance(val, list):
                lines.extend(_lines_for_list(val, max_items=7))
            else:
                lines.append(escape(_value_text(val)))
    elif section == "facts":
        display = (
            ("currency", "Currency"), ("languages", "Languages"),
            ("timezone", "Timezone"), ("payments", "Payments"),
            ("safety", "Safety"), ("plugs", "Electricity"),
            ("emergency", "Emergency numbers"),
            ("drivingSide", "Driving side"), ("driving", "Driving"),
            ("tapWaterSafe", "Tap water"), ("bestTimeToVisit", "Best time to visit"),
        )
        for key, label in display:
            value = facts.get(key)
            if value is not None:
                if isinstance(value, dict) and value.get("text"):
                    value = value["text"]
                elif key == "tapWaterSafe":
                    lines.append(
                        "• " + escape(label) + ": " + escape(
                            tr(language, "unknown_warning")
                        ) + " (source-specific)"
                    )
                    continue
                lines.append(f"• <b>{escape(label)}:</b> {escape(_value_text(value))}")
    elif section == "tips":
        for tip in (doc.get("tips") or [])[:16]:
            if isinstance(tip, dict):
                lines.append("• " + escape(str(tip.get("text") or "")[:700]))
    elif section == "faq":
        for question in (doc.get("faq") or [])[:16]:
            if isinstance(question, dict):
                lines.append("<b>" + escape(str(question.get("question") or "")) + "</b>")
                lines.append(escape(str(question.get("answer") or "")[:700]))
                lines.append("")
        lines.append("⚠️ " + escape(tr(language, "caution")))
    elif section == "sources":
        sources = [detail.record.get("source")]
        policy = doc.get("visaPolicy") or {}
        sources.append(policy.get("defaultSource"))
        sources.extend((doc.get("meta") or {}).get("primarySources") or [])
        for source in sources:
            if source:
                line = _source_line(source, language)
                if line and line not in lines:
                    lines.append(line)
        lines.append(
            external_link(
                f"https://travelrequirements.info/data/destinations/{doc.get('id')}.json",
                "Original JSON",
            )
        )
        lines.append(external_link(LICENSE_URL, "CC BY 4.0"))
    elif section == "transit":
        for key in ("transit", "entryModes", "levies"):
            item = doc.get(key)
            if item:
                lines.append(f"<b>{escape(key)}</b>")
                if isinstance(item, dict):
                    for k, v in list(item.items())[:12]:
                        lines.append("• " + escape(str(k)) + ": " + escape(_value_text(v)))
                else:
                    lines.append(escape(_value_text(item)))
        lines.append("⚠️ " + escape(tr(language, "caution")))
    else:
        return escape(tr(language, "unknown"))
    if len(lines) == 2:
        lines.append(escape(tr(language, "not_known")))
    lines.append("")
    lines.append(external_link(MAIN_SOURCE, tr(language, "license")))
    # Bound user-visible plain HTML to Telegram message limits.
    result = "\n".join(lines)
    if len(result) > 3850:
        result = "\n".join(lines[:max(3, len(lines) // 2)])
        if len(result) > 3700:
            result = result[:3700]
        result += "\n…\n" + external_link(MAIN_SOURCE, tr(language, "license"))
    return result


def render_rich_report(detail: VisaDetail, language: str) -> dict:
    """Native Telegram rich-message blocks (with standard HTML fallback)."""
    rule = detail.rule
    head = (
        f"<h3>{escape(tr(language, 'title'))}: "
        f"{escape(country_label(rule.destination, rule.country_name, language))}</h3>"
    )
    rows = [
        (tr(language, "passport"), rule.passport),
        (tr(language, "destination"), rule.destination),
        (tr(language, "status"), status_label(rule.status, language)),
        (tr(language, "stay"),
         str(rule.stay_days) if rule.stay_days is not None else tr(language, "not_known")),
        (tr(language, "checked"), rule.verified_on or tr(language, "not_known")),
    ]
    matrix = "<table bordered striped compact>" + "".join(
        f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in rows
    ) + "</table>"
    sections = []
    # These sections are individually available if native rich output is truncated.
    for key in ("types", "entry", "transit", "facts", "tips", "sources"):
        block = render_section(detail, language, key)
        block = block.replace("\n", "</p><p>")
        sections.append(f"<h3>{escape(tr(language, key))}</h3><p>{block}</p>")
    footer = f"<p>⚠️ {escape(tr(language, 'caution'))}</p>"
    html = head + matrix + "".join(sections) + footer
    if len(unescape(re.sub(r"<[^>]*>", "", html))) > 30_000:
        html = head + matrix + "".join(sections[:3]) + footer
    return {"html": html, "is_rtl": language in {"fa", "ar"}}


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
    rows.append([InlineKeyboardButton(tr(language, "search"), callback_data=f"visa:search:{purpose}")])
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


def detail_keyboard(language: str) -> InlineKeyboardMarkup:
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
    return InlineKeyboardMarkup(rows)


def section_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(language, "summary"), callback_data="visa:result")],
        [InlineKeyboardButton(tr(language, "another"), callback_data="visa:pick:d:0")],
    ])


def groups_keyboard(language: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(tr(language, group), callback_data=f"visa:list:{group}:0")]
        for group in ("all", "free", "evisa", "arrival", "required", "other")
    ]
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
