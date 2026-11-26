"""Read-only dataset registry inspection built on MarketMind foundation contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from marketmind.config import Settings
from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError


@dataclass(frozen=True, slots=True)
class IndustryDefinition:
    """Metadata describing a MarketMind supported industry vertical."""

    key: str
    label: str
    aliases: tuple[str, ...]
    description: str


SUPPORTED_INDUSTRIES: tuple[IndustryDefinition, ...] = (
    IndustryDefinition(
        key="retail",
        label="Retail & E-commerce",
        aliases=("retail", "retail & e-commerce", "ecommerce", "e-commerce"),
        description=(
            "Omnichannel merchandising, customer cohort retention, and basket economics."
        ),
    ),
    IndustryDefinition(
        key="banking",
        label="Banking & Marketing",
        aliases=("banking", "banking & marketing", "finance", "marketing"),
        description=(
            "Campaign response attribution, product adoption, and portfolio retention."
        ),
    ),
    IndustryDefinition(
        key="hospitality",
        label="Hospitality",
        aliases=("hospitality", "hotels", "travel"),
        description=(
            "Occupancy pacing, booking channel mix, and seasonal demand dynamics."
        ),
    ),
)

_ALIAS_TO_KEY: dict[str, str] = {
    alias: industry.key
    for industry in SUPPORTED_INDUSTRIES
    for alias in industry.aliases
}


def normalize_industry_key(industry: str) -> str | None:
    """Map a dataset industry string to a canonical supported industry key."""
    return _ALIAS_TO_KEY.get(industry.strip().lower())


@dataclass(frozen=True, slots=True)
class RegistryStatus:
    """Snapshot of dataset availability read from the configured data directory."""

    datasets: tuple[DatasetMetadata, ...]
    registry_path: Path
    registry_exists: bool
    error: str | None = None

    @property
    def total_datasets(self) -> int:
        """Return the number of validated registered datasets."""
        return len(self.datasets)

    @property
    def active_industry_count(self) -> int:
        """Return how many supported industries have at least one dataset."""
        active_keys = {
            key
            for dataset in self.datasets
            if (key := normalize_industry_key(dataset.industry)) is not None
        }
        return len(active_keys)

    def datasets_for_industry(self, industry_key: str) -> tuple[DatasetMetadata, ...]:
        """Return registered datasets belonging to the given canonical industry key."""
        return tuple(
            dataset
            for dataset in self.datasets
            if normalize_industry_key(dataset.industry) == industry_key
        )


def _parse_dataset_record(record: Any, index: int) -> DatasetMetadata:
    """Validate and convert a raw registry object into DatasetMetadata."""
    if not isinstance(record, dict):
        raise DataContractError(f"Registry entry at index {index} must be a JSON object")

    raw_created_at = record.get("created_at")
    if isinstance(raw_created_at, str):
        try:
            created_at: Any = datetime.fromisoformat(raw_created_at)
        except ValueError as exc:
            raise DataContractError(
                f"Registry entry {index} has invalid ISO-8601 created_at: {raw_created_at!r}"
            ) from exc
    else:
        created_at = raw_created_at

    return DatasetMetadata(
        dataset_id=record.get("dataset_id"),  # type: ignore[arg-type]
        name=record.get("name"),  # type: ignore[arg-type]
        industry=record.get("industry"),  # type: ignore[arg-type]
        created_at=created_at,
        source=record.get("source"),
    )


def inspect_registry(
    settings: Settings,
    registry_filename: str = "registry.json",
) -> RegistryStatus:
    """Inspect dataset availability under ``settings.data_dir`` without mutating state.

    A missing data directory or registry file is treated as a valid empty state.
    Malformed or contract-violating registry files are reported via ``RegistryStatus.error``.
    """
    relative_path = Path(registry_filename)
    requested_path = settings.data_dir / relative_path
    try:
        data_dir = settings.data_dir.resolve()
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("Registry filename must be a relative path inside data_dir")
        registry_path = requested_path.resolve()
        if not registry_path.is_relative_to(data_dir):
            raise ValueError("Registry filename resolves outside data_dir")
    except (OSError, RuntimeError, ValueError) as exc:
        return RegistryStatus(
            datasets=(),
            registry_path=requested_path,
            registry_exists=False,
            error=str(exc),
        )
    if not registry_path.exists():
        return RegistryStatus(
            datasets=(),
            registry_path=registry_path,
            registry_exists=False,
        )

    if registry_path.is_dir():
        return RegistryStatus(
            datasets=(),
            registry_path=registry_path,
            registry_exists=True,
            error=f"Expected a registry file, found directory: {registry_path}",
        )

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            entries = payload.get("datasets")
        else:
            entries = payload

        if not isinstance(entries, list):
            raise DataContractError(
                "Registry JSON must be a list of dataset entries or an object "
                "with a 'datasets' list"
            )

        datasets = tuple(
            _parse_dataset_record(entry, index) for index, entry in enumerate(entries)
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DataContractError) as exc:
        return RegistryStatus(
            datasets=(),
            registry_path=registry_path,
            registry_exists=True,
            error=str(exc),
        )

    return RegistryStatus(
        datasets=datasets,
        registry_path=registry_path,
        registry_exists=True,
    )
