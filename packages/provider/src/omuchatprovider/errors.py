class ProviderError(Exception):
    """Base class for provider errors."""

    pass


class ProviderFailed(ProviderError):
    """Raised when a provider fails to update a channel."""

    pass
