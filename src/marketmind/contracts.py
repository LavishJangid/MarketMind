"""Shared, dependency-free data contracts."""

from dataclasses import dataclass
from datetime import datetime

from marketmind.errors import DataContractError


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Identity and provenance metadata for a dataset handled by the platform."""

    dataset_id: str
    name: str
    industry: str
    created_at: datetime
    source: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("dataset_id", "name", "industry"):
            value = getattr(self, field_name)
            if not value.strip():
                raise DataContractError(f"{field_name} cannot be empty")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise DataContractError("created_at must include a timezone")
        if self.source is not None and not self.source.strip():
            raise DataContractError("source must be omitted or contain a non-empty value")
