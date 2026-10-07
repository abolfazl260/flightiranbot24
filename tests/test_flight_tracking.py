from datetime import timezone

import pytest

from flightiran.interfaces.telegram.flight import render_flight_result
from flightiran.modules.flight_tracking.domain import (
    FlightDetails,
    FlightSearchStatus,
)
from flightiran.modules.flight_tracking.provider import HttpFlightProvider
from flightiran.modules.flight_tracking.service import (
    FlightService,
    normalize_flight_number,
    timestamp_in_timezone,
)


class Provider:
    def __init__(self, value):
        self.value = value

    async def search(self, flight_number):
        return self.value


def test_normalization_and_timezone_conversion():
    assert normalize_flight_number(" klm-561 ") == "KLM561"
    assert normalize_flight_number("12345") is None
    converted = timestamp_in_timezone(0, "Asia/Tehran")
    assert converted is not None and converted.utcoffset().total_seconds() == 12600
    assert timestamp_in_timezone(0, "unknown/zone") is None


@pytest.mark.asyncio
async def test_all_search_states_are_explicit():
    found = FlightDetails("KLM561", airline="KLM")
    assert (
        await FlightService(Provider(found)).search("KLM561")
    ).status == FlightSearchStatus.FOUND
    assert (
        await FlightService(Provider(None)).search("KLM561")
    ).status == FlightSearchStatus.NOT_FOUND
    assert (
        await FlightService(Provider(found)).search("bad input!")
    ).status == FlightSearchStatus.INVALID
    assert (
        await FlightService(Provider(found), enabled=False).search("KLM561")
    ).status == FlightSearchStatus.DISABLED

    class Broken:
        async def search(self, number):
            raise RuntimeError("down")

    assert (await FlightService(Broken()).search("KLM561")).status == FlightSearchStatus.ERROR


def test_result_renderer_has_safe_buttons():
    result = FlightDetails("KLM561", airline="KLM", origin="AMS", destination="IKA")
    message, keyboard = render_flight_result(
        __import__(
            "flightiran.modules.flight_tracking.domain", fromlist=["FlightSearchResult"]
        ).FlightSearchResult(FlightSearchStatus.FOUND, result)
    )
    assert "KLM561" in message
    assert keyboard is not None


@pytest.mark.asyncio
async def test_http_provider_maps_payload_without_leaking_provider_shape():
    class Client:
        async def get_json(self, url, **kwargs):
            return {
                "flight": {
                    "callsign": "KLM561",
                    "airline": "KLM",
                    "scheduled_departure": 0,
                    "position": {"latitude": 35.0, "longitude": 51.0},
                }
            }

    flight = await HttpFlightProvider(Client(), "https://provider.test").search("KLM561")
    assert flight.airline == "KLM"
    assert flight.position.latitude == 35.0
    assert flight.scheduled_departure.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_http_provider_maps_flightradar24_search_and_detail_payload():
    class Client:
        def __init__(self):
            self.payloads = [
                {"results": [{"id": "abc123", "detail": {"lat": 35.7, "lon": 51.4}}]},
                {
                    "identification": {"callsign": "KLM561"},
                    "airline": {"name": "KLM"},
                    "aircraft": {
                        "model": {"text": "Boeing 737"},
                        "age": 8,
                        "images": {"large": [{"src": "https://img.test/plane.jpg"}]},
                    },
                    "airport": {
                        "origin": {
                            "name": "Amsterdam Schiphol",
                            "position": {
                                "region": {"city": "Amsterdam"},
                                "country": {"name": "Netherlands"},
                            },
                            "info": {"terminal": "1"},
                            "timezone": {"offset": 3600},
                        },
                        "destination": {
                            "name": "Imam Khomeini",
                            "position": {
                                "region": {"city": "Tehran"},
                                "country": {"name": "Iran"},
                            },
                            "info": {"terminal": "A"},
                            "timezone": {"offset": 12600},
                        },
                    },
                    "time": {
                        "scheduled": {"departure": 1767355200, "arrival": 1767376800},
                        "real": {"departure": 1767355500},
                        "estimated": {"arrival": 1767377400},
                    },
                },
            ]
            self.calls = []

        async def get_json(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return self.payloads.pop(0)

    client = Client()
    flight = await HttpFlightProvider(client, "https://fr24.test/search").search("KLM561")
    assert flight is not None
    assert flight.airline == "KLM"
    assert flight.origin_country == "Netherlands"
    assert flight.destination_city == "Tehran"
    assert flight.origin_terminal == "1"
    assert flight.aircraft_age == 8
    assert flight.aircraft_image == "https://img.test/plane.jpg"
    assert flight.position.latitude == 35.7
    assert flight.scheduled_departure.utcoffset().total_seconds() == 3600
    assert flight.scheduled_arrival.utcoffset().total_seconds() == 12600
    assert flight.map_url.endswith("/abc123")
    assert flight.history_url.endswith("/KLM561")
    assert client.calls[1][1]["params"] == {"version": "1.5", "flight": "abc123"}
