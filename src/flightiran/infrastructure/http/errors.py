"""Provider errors with safe, stable categories."""


class ProviderError(RuntimeError):
    """Base class for errors exposed by provider adapters."""


class ProviderTimeout(ProviderError):
    """Provider did not respond before the configured timeout."""


class ProviderHTTPError(ProviderError):
    """Provider returned a non-success HTTP status."""

    def __init__(self, status_code: int, provider: str) -> None:
        self.status_code = status_code
        self.provider = provider
        super().__init__(f"Provider {provider} returned HTTP {status_code}")


class ProviderRateLimited(ProviderHTTPError):
    """Provider requested that the caller slow down."""


class ProviderInvalidResponse(ProviderError):
    """Provider returned malformed JSON or an invalid DTO."""
