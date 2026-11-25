import logging

from marketmind.config import Settings
from marketmind.logging import configure_logging


def test_logging_configuration_uses_settings(monkeypatch) -> None:
    calls = {}
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])

    def capture_basic_config(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", capture_basic_config)
    configure_logging(Settings(log_level="WARNING"))
    assert calls["level"] == logging.WARNING
    assert "%(name)s" in calls["format"]


def test_existing_root_handler_is_preserved_and_level_is_configured(monkeypatch) -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler()
    monkeypatch.setattr(root, "handlers", [handler])
    monkeypatch.setattr(root, "level", logging.NOTSET)

    configure_logging(Settings(log_level="WARNING"))

    assert root.handlers == [handler]
    assert root.level == logging.WARNING


def test_repeated_configuration_does_not_duplicate_handlers(monkeypatch) -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler()
    monkeypatch.setattr(root, "handlers", [handler])

    settings = Settings(log_level="ERROR")
    configure_logging(settings)
    first_handlers = list(root.handlers)
    configure_logging(settings)

    assert root.handlers == first_handlers == [handler]
    assert root.level == logging.ERROR
