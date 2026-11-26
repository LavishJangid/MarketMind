import logging

from marketmind.config import Settings
from marketmind.logging import configure_logging


def test_logging_configuration_uses_settings(monkeypatch) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    configure_logging(Settings(log_level="WARNING"))
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert handler.level == logging.WARNING
    assert handler.formatter is not None
    assert "%(name)s" in handler.formatter._fmt


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


def test_repeated_configuration_refreshes_marketmind_handler(monkeypatch) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])

    configure_logging(Settings(log_level="WARNING"))
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert handler.level == logging.WARNING
    assert handler.formatter is not None

    configure_logging(Settings(log_level="DEBUG"))
    assert root.handlers == [handler]
    assert root.level == logging.DEBUG
    assert handler.level == logging.DEBUG
    assert handler.formatter is not None
    assert handler.formatter._fmt == "%(asctime)s %(levelname)s %(name)s %(message)s"


def test_external_handlers_are_preserved_without_reconfiguration(monkeypatch) -> None:
    root = logging.getLogger()
    external = logging.StreamHandler()
    external.setLevel(logging.CRITICAL)
    formatter = logging.Formatter("%(message)s external")
    external.setFormatter(formatter)
    monkeypatch.setattr(root, "handlers", [external])

    configure_logging(Settings(log_level="WARNING"))
    configure_logging(Settings(log_level="ERROR"))

    assert root.handlers == [external]
    assert root.level == logging.ERROR
    assert external.level == logging.CRITICAL
    assert external.formatter is formatter
