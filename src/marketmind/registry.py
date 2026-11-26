"""Backend registry data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    """Dataset metadata paired with a portable path relative to the data root.

    The storage path uses POSIX separators so serialized records have the same
    representation across operating systems. Filesystem resolution and access
    are responsibilities of the future registry service, not this value object.
    """

    metadata: DatasetMetadata
    storage_path: PurePosixPath

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, DatasetMetadata):
            raise DataContractError("metadata must be a DatasetMetadata instance")
        if not isinstance(self.storage_path, PurePosixPath):
            raise DataContractError("storage_path must be a PurePosixPath")

        path_text = str(self.storage_path)
        if (
            not self.storage_path.parts
            or self.storage_path == PurePosixPath(".")
            or self.storage_path.is_absolute()
            or ".." in self.storage_path.parts
            or "\\" in path_text
            or ":" in path_text
            or "\0" in path_text
        ):
            raise DataContractError(
                "storage_path must be a non-empty relative path without traversal"
            )
