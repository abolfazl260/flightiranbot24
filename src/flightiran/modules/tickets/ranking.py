"""Version 1 fare ranking shared by public projections and Telegram."""

import math

MAX_TOMAN = 1_000_000_000_000


def valid_price(value: object) -> bool:
    return type(value) is int and 0 < value <= MAX_TOMAN


def valid_drop_percent(price: object, average: object, count: object) -> float | None:
    if (not valid_price(price) or type(average) not in (int, float)
            or not math.isfinite(average) or not price < average <= MAX_TOMAN
            or type(count) is not int or not 3 <= count <= 100_000):
        return None
    # Positive half-up tenths, identical to Kotlin / JavaScript (not banker's rounding).
    value = math.floor((average - price) * 1000 / average + 0.5) / 10
    return value if value > 0 else None
