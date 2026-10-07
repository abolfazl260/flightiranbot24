from datetime import datetime, timezone
from pathlib import Path

import pytest

from flightiran.interfaces.telegram.airport import airport_keyboard, render_board
from flightiran.modules.airport import (
    AirportBoard,
    AirportCatalog,
    AirportService,
    BoardFlight,
    BoardStatus,
)

DATA = Path("src/flightiran/modules/airport/data/airports.json")


class Provider:
    def __init__(self, board):
        self._board = board

    async def board(self, airport, direction):
        return self._board


def catalog():
    return AirportCatalog.from_json(DATA)


def test_catalog_lookup_and_search_are_configuration_backed():
    airports = catalog()
    assert len(airports.all()) == 28
    assert airports.get(" ika ").display_name("fa") == "امام خمینی تهران"
    assert airports.search("London")[0].code == "LHR"


def test_airport_keyboard_is_paginated():
    airports = catalog().all()
    first = airport_keyboard(airports, page=0, page_size=8)
    second = airport_keyboard(airports, page=1, page_size=8)
    assert len(first.inline_keyboard) == 9
    assert len(second.inline_keyboard) == 9
    assert len(first.inline_keyboard[0]) == 1


@pytest.mark.asyncio
async def test_service_and_board_states_render():
    airport = catalog().get("IKA")
    board = AirportBoard(
        airport=airport,
        direction="arrivals",
        status=BoardStatus.OK,
        flights=(
            BoardFlight("IR123", "Iran Air", "FRA", "IKA", datetime.now(timezone.utc), "On time"),
        ),
    )
    result = await AirportService(catalog(), Provider(board)).get_board("IKA", "arrivals")
    assert result.flights[0].flight_number == "IR123"
    assert "IR123" in render_board(result)
    empty = AirportBoard(airport, "departures", BoardStatus.EMPTY)
    assert "پیدا نشد" in render_board(empty)


@pytest.mark.asyncio
async def test_provider_error_is_normalized():
    class Broken:
        async def board(self, airport, direction):
            raise RuntimeError("provider down")

    result = await AirportService(catalog(), Broken()).get_board("IKA", "arrivals")
    assert result.status == BoardStatus.ERROR
    with pytest.raises(ValueError):
        await AirportService(catalog(), Broken()).get_board("XXX", "arrivals")
