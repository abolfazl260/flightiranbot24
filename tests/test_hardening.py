from flightiran.config import Settings
from flightiran.health import RuntimeMetrics, healthcheck


def test_production_validation_and_health_metrics():
    settings = Settings(TELEGRAM_BOT_TOKEN="123456:AA-valid-token", APP_ENV="production")
    settings.validate_for_production()
    metrics = RuntimeMetrics()
    metrics.increment("commands")
    assert metrics.snapshot()["counters"] == {"commands": 1}
    assert healthcheck(settings.database_url)["status"] == "ok"
