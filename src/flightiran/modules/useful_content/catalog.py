"""Domain catalogue for the travel information menu.

The catalogue deliberately contains data, rather than Telegram objects.  This
keeps content updates independent from the interface and makes the catalogue
easy to replace with a database-backed repository later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class UsefulLink:
    """A user-facing travel resource with a stable identifier."""

    id: str
    title: str
    url: str
    category: str = "general"
    description: str = ""
    checked_on: date | None = None
    active: bool = True

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Useful link must use an absolute HTTP(S) URL: {self.url!r}")


class UsefulContentCatalog:
    """Read-only content access with deterministic ordering."""

    def __init__(self, links: tuple[UsefulLink, ...] | list[UsefulLink]) -> None:
        self._links = tuple(links)
        ids = [link.id for link in self._links]
        if len(ids) != len(set(ids)):
            raise ValueError("Useful link ids must be unique")

    def all(self) -> tuple[UsefulLink, ...]:
        return tuple(link for link in self._links if link.active)

    def by_category(self, category: str) -> tuple[UsefulLink, ...]:
        return tuple(link for link in self.all() if link.category == category)

    def get(self, link_id: str) -> UsefulLink | None:
        return next((link for link in self.all() if link.id == link_id), None)


def default_catalog() -> UsefulContentCatalog:
    """Return the initial catalogue migrated from the legacy bot.

    Telegram post URLs are retained for existing editorial content.  They are
    still represented as external links, so replacing them with official
    sources later does not require a code change.
    """

    links = (
        UsefulLink("flight-compensation", "جبران خسارت پرواز ✈️", "https://www.airhelp.com/"),
        UsefulLink("airline-ratings", "رتبه‌بندی ایرلاین‌ها 🛩️", "https://airlineratings.com"),
        UsefulLink("exit-ban", "ممنوع‌الخروجی ❌", "https://t.me/koolbar_international/527"),
        UsefulLink(
            "prohibited-items", "کالاهای ممنوعه 🚫", "https://t.me/koolbar_international/637"
        ),
        UsefulLink("exit-fees", "عوارض خروج از کشور 💳", "https://t.me/koolbar_international/516"),
        UsefulLink("travel-insurance", "بیمه مسافرتی 🛡️", "https://t.me/koolbar_international/549"),
        UsefulLink("travel-tips", "نکات سفر 💡", "https://t.me/koolbar_international/1254"),
        UsefulLink("get-passport", "دریافت پاسپورت 🗂️", "https://t.me/koolbar_international/526"),
        UsefulLink(
            "academic-exemption", "معافیت تحصیلی 🎓", "https://t.me/koolbar_international/503"
        ),
        UsefulLink(
            "flight-rules-iran",
            "ایران 🇮🇷",
            "https://www.alibaba.ir/mag/travel-facts/customs-regulations-travelers-luggage/",
            "flight-rules",
        ),
        UsefulLink(
            "flight-rules-canada",
            "کانادا 🇨🇦",
            "https://t.me/koolbar_international/81",
            "flight-rules",
        ),
        UsefulLink(
            "flight-rules-italy",
            "ایتالیا 🇮🇹",
            "https://t.me/koolbar_international/508",
            "flight-rules",
        ),
        UsefulLink(
            "flight-rules-uk",
            "بریتانیا 🇬🇧",
            "https://t.me/koolbar_international/540",
            "flight-rules",
        ),
        UsefulLink(
            "flight-rules-usa",
            "آمریکا 🇺🇸",
            "https://t.me/koolbar_international/542",
            "flight-rules",
        ),
        UsefulLink(
            "flight-rules-europe",
            "اروپا 🇪🇺",
            "https://t.me/koolbar_international/636",
            "flight-rules",
        ),
        UsefulLink(
            "travel-sites-canada",
            "کانادا 🇨🇦",
            "https://t.me/koolbar_international/560",
            "travel-sites",
        ),
        UsefulLink(
            "travel-sites-italy",
            "ایتالیا 🇮🇹",
            "https://t.me/koolbar_international/562",
            "travel-sites",
        ),
        UsefulLink(
            "travel-sites-iraq", "عراق 🇮🇶", "https://t.me/koolbar_international/566", "travel-sites"
        ),
        UsefulLink(
            "travel-sites-uk",
            "بریتانیا 🇬🇧",
            "https://t.me/koolbar_international/563",
            "travel-sites",
        ),
        UsefulLink(
            "travel-sites-usa",
            "آمریکا 🇺🇸",
            "https://t.me/koolbar_international/564",
            "travel-sites",
        ),
        UsefulLink(
            "travel-sites-europe",
            "اروپا 🇪🇺",
            "https://t.me/koolbar_international/565",
            "travel-sites",
        ),
    )
    return UsefulContentCatalog(links)
