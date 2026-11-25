"""Application configuration and environment loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from marketmind.errors import ConfigurationError


def _parse_bool(name: str, value: str) -> bool:
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
            if not raw_data_dir.strip() or "\0" in raw_data_dir:
                raise ValueError
            data_dir = Path(raw_data_dir)
        except (TypeError, ValueError, OSError) as exc:
            raise ConfigurationError("data_dir must be a non-empty, valid path") from exc
        object.__setattr__(self, "data_dir", data_dir)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Load settings from ``MARKETMIND_*`` variables."""
        values = os.environ if environ is None else environ
        debug = _parse_bool("MARKETMIND_DEBUG", values.get("MARKETMIND_DEBUG", "false"))
        return cls(
            app_name=values.get("MARKETMIND_APP_NAME", "MarketMind"),
            environment=values.get("MARKETMIND_ENVIRONMENT", "development"),
            log_level=values.get("MARKETMIND_LOG_LEVEL", "DEBUG" if debug else "INFO"),
            data_dir=Path(values.get("MARKETMIND_DATA_DIR", "data")),
            debug=debug,
        )
