"""Airport use cases independent of Telegram and provider JSON."""

from .catalog import AirportRepository
from .domain import AirportBoard, BoardStatus
from .provider import AirportProvider


class AirportService:
    def __init__(self, repository: AirportRepository, provider: AirportProvider) -> None:
        self.repository = repository
        self.provider = provider

    async def get_board(self, code: str, direction: str) -> AirportBoard:
        airport = self.repository.get(code)
        if airport is None:
            raise ValueError(f"Unknown airport code: {code}")
        if direction not in {"arrivals", "departures"}:
            raise ValueError("direction must be arrivals or departures")
        try:
            return await self.provider.board(airport, direction)
        except Exception as exc:
            return AirportBoard(airport, direction, BoardStatus.ERROR, message=str(exc))
