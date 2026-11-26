"""Backend registry data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from marketmind.config import Settings
from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError


def _validate_storage_path(storage_path: PurePosixPath) -> None:
    """Validate the portable relative path shape used by registry records."""
    if not isinstance(storage_path, PurePosixPath):
        raise DataContractError("storage_path must be a PurePosixPath")

    path_text = str(storage_path)
    if (
        not storage_path.parts
        or storage_path == PurePosixPath(".")
        or storage_path.is_absolute()
        or ".." in storage_path.parts
        or "\\" in path_text
        or ":" in path_text
        or "\0" in path_text
    ):
        raise DataContractError(
            "storage_path must be a non-empty relative path without traversal"
        )


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
        _validate_storage_path(self.storage_path)


def resolve_storage_path(
    settings: Settings,
    record_or_path: DatasetRecord | PurePosixPath,
) -> Path:
    """Resolve a record's storage path beneath ``Settings.data_dir``.

    The returned path is absolute and normalized after resolving existing
    symlinks. A missing target (including missing parent directories) is valid
    and is returned without creating anything, so ingestion can resolve its
    destination before writing. Callers can use ``Path.exists()`` to distinguish
    an existing target from a valid future destination.

    Raises:
        DataContractError: If the path is malformed, cannot be safely resolved,
            or resolves outside the configured data root.
    """
    if isinstance(record_or_path, DatasetRecord):
        storage_path = record_or_path.storage_path
    elif isinstance(record_or_path, PurePosixPath):
        storage_path = record_or_path
    else:
        raise DataContractError(
            "record_or_path must be a DatasetRecord or PurePosixPath"
        )

    _validate_storage_path(storage_path)

    try:
        data_root = settings.data_dir.resolve()
        resolved_path = (data_root / Path(*storage_path.parts)).resolve()
    except (OSError, RuntimeError, ValueError):
        raise DataContractError("storage path could not be safely resolved") from None

    if not resolved_path.is_relative_to(data_root):
        raise DataContractError("storage path resolves outside the configured data root")

    return resolved_path
