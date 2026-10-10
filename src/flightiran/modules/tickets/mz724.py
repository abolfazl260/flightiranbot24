"""Adapter for the cheap-ticket table published by mz724.ir."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from flightiran.infrastructure.http import ProviderHttpClient
from flightiran.infrastructure.http.errors import ProviderInvalidResponse

from .domain import CheapTicketDestination, CheapTicketRoute

LOGGER = logging.getLogger(__name__)


class Mz724TicketProvider:
    """Download and normalize mz724's HTML without exposing HTML to the UI."""

    def __init__(
        self,
        http: ProviderHttpClient,
        *,
        url: str = "https://mz724.ir/",
    ) -> None:
        self.http = http
        self.url = url

    async def routes(self) -> list[CheapTicketRoute]:
        html = await self.http.get_text(
            self.url,
            provider="mz724",
            headers={"User-Agent": "FlightIranBot/2.0 (+https://mz724.ir/)"},
            cache_key="mz724:cheap-ticket-routes",
        )
        return parse_routes(html, source_url=self.url)


def parse_routes(document: str, *, source_url: str = "https://mz724.ir/") -> list[CheapTicketRoute]:
    """Parse the provider's ``sr_table`` rows into stable internal models.

    The site has historically rendered a ``t_table`` origin and ``line`` links.
    Missing or malformed rows are skipped, while an entirely unusable document
    raises a provider error so the handler can show a useful failure message.
    """
    soup = BeautifulSoup(document, "html.parser")
    routes: list[CheapTicketRoute] = []
    for table in soup.select("div.sr_table"):
        origin_node = table.select_one("div.t_table")
        if origin_node is None:
            continue
        origin = " ".join(origin_node.get_text(" ", strip=True).split())
        destinations: list[CheapTicketDestination] = []
        for line in table.select("a.line"):
            city_node = line.select_one(".city")
            price_node = line.select_one(".price")
            if city_node is None or price_node is None:
                continue
            city = " ".join(city_node.get_text(" ", strip=True).split())
            price = " ".join(price_node.get_text(" ", strip=True).split())
            if city and price:
                destinations.append(CheapTicketDestination(city, price))
        if origin and destinations:
            routes.append(CheapTicketRoute(origin, tuple(destinations), source_url))
    if not routes:
        raise ProviderInvalidResponse("Ticket route data is unavailable")
    return routes
