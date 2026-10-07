"""Provider contracts and DTO validation boundary."""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .errors import ProviderInvalidResponse

ModelT = TypeVar("ModelT", bound=BaseModel)


class ProviderClient(Protocol):
    async def get_json(self, url: str, *, provider: str, **kwargs: Any) -> dict[str, Any]: ...


def validate_dto(model: type[ModelT], payload: dict[str, Any], provider: str) -> ModelT:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ProviderInvalidResponse(f"Provider {provider} returned an invalid response") from exc
