"""Application configuration and environment loading."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from marketmind.errors import ConfigurationError


def _parse_bool(name: str, value: str) -> bool:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a boolean value represented as text")
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean value, got {value!r}")


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings shared by MarketMind services."""

    app_name: str = "MarketMind"
    environment: str = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    debug: bool = False

    def __post_init__(self) -> None:
        for field_name in ("app_name", "environment", "log_level"):
            if not isinstance(getattr(self, field_name), str):
                raise ConfigurationError(f"{field_name} must be a string")
        if not isinstance(self.debug, bool):
            raise ConfigurationError("debug must be a boolean")
        if not self.app_name.strip():
            raise ConfigurationError("app_name cannot be empty")
        if not self.environment.strip():
            raise ConfigurationError("environment cannot be empty")
        if self.log_level.upper() not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ConfigurationError(f"Unsupported log level: {self.log_level!r}")
        log_level = self.log_level.upper()
        if self.debug:
            log_level = "DEBUG"
        object.__setattr__(self, "log_level", log_level)
        object.__setattr__(self, "debug", log_level == "DEBUG")

        try:
            raw_data_dir = os.fspath(self.data_dir)
            if (
                not isinstance(raw_data_dir, str)
                or not raw_data_dir.strip()
                or "\0" in raw_data_dir
            ):
                raise ValueError
            data_dir = Path(raw_data_dir)
        except (TypeError, ValueError, OSError) as exc:
            raise ConfigurationError("data_dir must be a non-empty, valid path") from exc
        object.__setattr__(self, "data_dir", data_dir)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Load settings from ``MARKETMIND_*`` variables."""
        values = os.environ if environ is None else environ
        if not isinstance(values, Mapping):
            raise ConfigurationError("environment settings must be a mapping of strings")

        defaults = {
            "MARKETMIND_DEBUG": "false",
            "MARKETMIND_APP_NAME": "MarketMind",
            "MARKETMIND_ENVIRONMENT": "development",
            "MARKETMIND_DATA_DIR": "data",
        }
        env_values: dict[str, str] = {}
        for name, default in defaults.items():
            value = values.get(name, default)
            if not isinstance(value, str):
                raise ConfigurationError(f"{name} must be a string")
            env_values[name] = value
        debug = _parse_bool("MARKETMIND_DEBUG", env_values["MARKETMIND_DEBUG"])
        if "MARKETMIND_LOG_LEVEL" in values:
            log_level = values["MARKETMIND_LOG_LEVEL"]
            if not isinstance(log_level, str):
                raise ConfigurationError("MARKETMIND_LOG_LEVEL must be a string")
        else:
            log_level = "DEBUG" if debug else "INFO"
        return cls(
            app_name=env_values["MARKETMIND_APP_NAME"],
            environment=env_values["MARKETMIND_ENVIRONMENT"],
            log_level=log_level,
            data_dir=env_values["MARKETMIND_DATA_DIR"],
            debug=debug,
        )
