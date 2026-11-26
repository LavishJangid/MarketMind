from pathlib import Path

import pytest

from marketmind.config import Settings
from marketmind.errors import ConfigurationError


def test_settings_use_defaults() -> None:
    assert Settings.from_env({}) == Settings()


def test_settings_parse_environment_values() -> None:
    settings = Settings.from_env(
        {
            "MARKETMIND_APP_NAME": "Retail BI",
            "MARKETMIND_ENVIRONMENT": "staging",
            "MARKETMIND_LOG_LEVEL": "debug",
            "MARKETMIND_DATA_DIR": "warehouse",
            "MARKETMIND_DEBUG": "yes",
        }
    )
    assert settings.app_name == "Retail BI"
    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == Path("warehouse")
    assert settings.debug is True


@pytest.mark.parametrize("value", ["maybe", "", "2"])
def test_invalid_debug_value_is_rejected(value: str) -> None:
    with pytest.raises(ConfigurationError, match="boolean"):
        Settings.from_env({"MARKETMIND_DEBUG": value})


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="log level"):
        Settings(log_level="TRACE")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("app_name", 1),
        ("environment", None),
        ("log_level", 10),
        ("debug", "false"),
    ],
)
def test_invalid_direct_setting_types_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ConfigurationError, match=field):
        Settings(**{field: value})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MARKETMIND_APP_NAME", 1),
        ("MARKETMIND_ENVIRONMENT", None),
        ("MARKETMIND_LOG_LEVEL", 20),
        ("MARKETMIND_DEBUG", 1),
        ("MARKETMIND_DATA_DIR", b"data"),
    ],
)
def test_invalid_environment_types_are_rejected(name: str, value: object) -> None:
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_env({name: value})  # type: ignore[dict-item]


def test_non_mapping_environment_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="mapping"):
        Settings.from_env([])  # type: ignore[arg-type]


def test_explicit_empty_environment_log_level_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="log level"):
        Settings.from_env({"MARKETMIND_LOG_LEVEL": ""})


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_data_directory_is_rejected(value: str) -> None:
    with pytest.raises(ConfigurationError, match="data_dir"):
        Settings(data_dir=value)


def test_invalid_data_directory_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="data_dir"):
        Settings(data_dir="invalid\0path")


def test_debug_and_log_level_are_consistent_for_direct_construction() -> None:
    assert Settings(debug=True).log_level == "DEBUG"
    assert Settings(log_level="DEBUG").debug is True
    assert Settings(debug=True, log_level="WARNING").log_level == "DEBUG"


def test_debug_and_log_level_are_consistent_for_environment_settings() -> None:
    debug_enabled = Settings.from_env({"MARKETMIND_DEBUG": "true"})
    debug_level = Settings.from_env({"MARKETMIND_LOG_LEVEL": "debug"})
    assert debug_enabled.log_level == "DEBUG"
    assert debug_level.debug is True
