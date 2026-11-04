"""All currently active native home destinations have a reachable Mini App entry."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_native_destinations_have_web_navigation_and_platform_specific_privacy():
    native = (ROOT / "android/app/src/main/java/com/abolfazl260/flightiranbot24/data/"
              "LocalHomeRepository.kt").read_text()
    html = (ROOT / "src/flightiran/webapp/static/index.html").read_text()
    mapping = {
        "OFFLINE_CHECKLIST": 'data-go="checklist"',
        "TICKET_PRICES": 'data-go="tickets"',
        "IRAN_FLIGHTS": 'data-go="fids"',
        "OFFLINE_AIRPORTS": 'data-go="airports"',
        "AIRLINES": 'data-go="airlines"',
        "TELEGRAM_BOT": 'data-link="bot"',
        "TELEGRAM_VISA": 'data-go="visa"',
        "TELEGRAM_USEFUL": 'data-go="websites"',
        "SUPPORT": 'data-link="support"',
        "PRIVACY": 'data-go="privacy"',
    }
    for destination, link in mapping.items():
        assert "HomeDestination." + destination in native
        assert link in html
    assert 'id="privacy-clear-visa"' in html
    assert 'id="privacy-checklist"' in html
    assert "ورود مینی‌اپ از طریق تلگرام است" in html
    assert "مدت نگهداری دقیق از این رابط مشخص نیست" in html


def test_popular_visa_destinations_match_native():
    native = (ROOT / "android/app/src/main/java/com/abolfazl260/flightiranbot24/data/visa/"
              "VisaCountries.kt").read_text()
    web = (ROOT / "src/flightiran/webapp/static/mobile-parity.mjs").read_text()
    import re
    codes = re.search(r'val popular = listOf\((.*?)\)', native).group(1)
    expected = re.findall(r'"([A-Z]{2})"', codes)
    actual = re.search(r'POPULAR_VISA=\[(.*?)\]', web).group(1)
    assert re.findall(r"'([A-Z]{2})'", actual) == expected
