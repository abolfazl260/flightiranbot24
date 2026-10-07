"""Lightweight APScheduler integration for alert polling."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class FlightAlertScheduler:
    def __init__(self, poller, interval_seconds: int = 60) -> None:
        self.poller = poller
        self.scheduler = AsyncIOScheduler()
        self.interval_seconds = interval_seconds

    def start(self) -> None:
        self.scheduler.add_job(
            self.poller,
            "interval",
            seconds=self.interval_seconds,
            id="flight-alerts",
            replace_existing=True,
        )
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
