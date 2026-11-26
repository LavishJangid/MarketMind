"""Explicit logging configuration without changing global state at import."""

import logging

from marketmind.config import Settings

_HANDLER_MARKER = "_marketmind_configured_handler"
_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> None:
    """Configure the root logger using validated application settings."""
    root = logging.getLogger()
    level = getattr(logging, settings.log_level)
    root.setLevel(level)

    configured_handler = next(
        (handler for handler in root.handlers if getattr(handler, _HANDLER_MARKER, False)),
        None,
    )
    if configured_handler is not None:
        configured_handler.setLevel(level)
        configured_handler.setFormatter(logging.Formatter(_FORMAT))
    elif not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(_FORMAT))
        setattr(handler, _HANDLER_MARKER, True)
        root.addHandler(handler)
