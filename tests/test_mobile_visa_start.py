"""Android visa-alert /start payload contract: fixed shape, no auto-subscription."""

from flightiran.interfaces.telegram.visa_flow import parse_visa_start_payload


def test_mobile_visa_start_accepts_only_two_iso_country_codes() -> None:
    assert parse_visa_start_payload("visa_IR_TR") == ("IR", "TR")
    assert parse_visa_start_payload("visa_AF_DE") == ("AF", "DE")
    assert parse_visa_start_payload("visa") is None
    assert parse_visa_start_payload("visa_ir_tr") is None
    assert parse_visa_start_payload("visa_IR_TR_more") is None
    assert parse_visa_start_payload("visa_IR_TR?admin=1") is None
    assert parse_visa_start_payload("visa_IR_../") is None
