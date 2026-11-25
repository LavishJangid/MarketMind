"""Explicit logging configuration without changing global state at import."""

import logging

from marketmind.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure the root logger using validated application settings."""
    root = logging.getLogger()
    level = getattr(logging, settings.log_level)
    if root.handlers:
        # Respect handlers installed by a host application while still applying
        # MarketMind's requested filtering level.
        root.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
