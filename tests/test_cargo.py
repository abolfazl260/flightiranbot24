from datetime import date

import pytest

from flightiran.modules.cargo import CapacityOffer, CargoMarketplace, CargoRequest, CargoStatus


def test_verified_matching_and_state_transitions():
    market = CargoMarketplace()
    request = CargoRequest(1, 1, "IKA", "FRA", date(2026, 2, 1), "document", 2, 1, 100, True)
    offer = CapacityOffer(1, 2, "IKA", "FRA", date(2026, 2, 1), 5, True)
    published = market.publish_request(request)
    market.publish_offer(offer)
    assert market.matches(published) == [offer]
    assert market.transition(1, CargoStatus.CANCELLED).status == CargoStatus.CANCELLED


def test_unverified_or_incomplete_cargo_is_rejected():
    market = CargoMarketplace()
    with pytest.raises(ValueError):
        market.publish_request(CargoRequest(1, 1, "IKA", "FRA", date.today(), "", 1, 1, 1, False))
