"""Versioned, searchable traveler rules articles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RuleArticle:
    id: str
    title: str
    body: str
    category: str
    countries: tuple[str, ...]
    source_url: str
    checked_on: date
    valid_until: date | None = None
    version: str = "1"
    active: bool = True

    @property
    def expired(self) -> bool:
        return self.valid_until is not None and self.valid_until < date.today()


class RulesRepository:
    def __init__(self, articles: list[RuleArticle] | None = None) -> None:
        self._articles = list(articles or [])

    def add(self, article: RuleArticle) -> None:
        self._articles.append(article)

    def search(
        self, query: str, category: str | None = None, country: str | None = None
    ) -> list[RuleArticle]:
        needle = query.casefold()
        return [
            article
            for article in self._articles
            if article.active
            and not article.expired
            and (not category or article.category == category)
            and (not country or country in article.countries)
            and (needle in article.title.casefold() or needle in article.body.casefold())
        ]
