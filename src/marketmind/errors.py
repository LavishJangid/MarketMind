"""Shared exception types for clear error handling across modules."""


class MarketMindError(Exception):
    """Base class for expected MarketMind application errors."""


class ConfigurationError(MarketMindError, ValueError):
    """Raised when application configuration is invalid."""


class DataContractError(MarketMindError, ValueError):
    """Raised when supplied data violates a shared contract."""
