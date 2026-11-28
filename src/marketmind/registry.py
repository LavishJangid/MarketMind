"""Backend registry data contracts."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from marketmind.config import Settings
from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError, MarketMindError

REGISTRY_FILENAME = "registry.json"
REGISTRY_SCHEMA_VERSION = 1


class RegistryFormatError(MarketMindError, ValueError):
    """Raised when a registry file is malformed or uses an unsupported format."""


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


def _parse_metadata(payload: Any, *, strict: bool) -> DatasetMetadata:
    if not isinstance(payload, dict):
        raise RegistryFormatError("Registry record metadata must be a JSON object")

    required_fields = {"dataset_id", "name", "industry", "created_at"}
    allowed_fields = required_fields | {"source"}
    if strict and not required_fields.issubset(payload):
        raise RegistryFormatError("Versioned registry metadata is missing required fields")
    if strict and not set(payload).issubset(allowed_fields):
        raise RegistryFormatError("Versioned registry metadata has unsupported fields")

    created_at = payload.get("created_at")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except ValueError:
            raise DataContractError("created_at must be a valid ISO-8601 datetime") from None

    return DatasetMetadata(
        dataset_id=payload.get("dataset_id"),
        name=payload.get("name"),
        industry=payload.get("industry"),
        created_at=created_at,
        source=payload.get("source"),
    )


def _parse_versioned_record(payload: Any) -> DatasetRecord:
    if not isinstance(payload, dict) or set(payload) != {"metadata", "storage_path"}:
        raise RegistryFormatError(
            "Versioned registry records must contain only metadata and storage_path"
        )

    storage_path = payload["storage_path"]
    if not isinstance(storage_path, str):
        raise RegistryFormatError("storage_path must be a relative path string")

    metadata = _parse_metadata(payload["metadata"], strict=True)
    return DatasetRecord(metadata, PurePosixPath(storage_path))


def _parse_legacy_record(payload: Any, index: int) -> DatasetRecord:
    if not isinstance(payload, dict):
        raise RegistryFormatError(f"Legacy registry entry {index} must be a JSON object")
    if "storage_path" not in payload:
        raise RegistryFormatError(
            f"Legacy registry entry {index} has no storage_path and cannot be mapped "
            "to DatasetRecord without inventing a path"
        )

    storage_path = payload["storage_path"]
    if not isinstance(storage_path, str):
        raise RegistryFormatError(f"Legacy registry entry {index} storage_path must be a string")

    metadata = _parse_metadata(payload, strict=False)
    return DatasetRecord(metadata, PurePosixPath(storage_path))


def _parse_registry_payload(payload: Any) -> tuple[DatasetRecord, ...]:
    """Parse the supported versioned schema and safe legacy shapes."""
    is_legacy = False
    if isinstance(payload, list):
        entries = payload
        is_legacy = True
    elif isinstance(payload, dict) and "schema_version" in payload:
        version = payload["schema_version"]
        if type(version) is not int or version != REGISTRY_SCHEMA_VERSION:
            raise RegistryFormatError("Registry schema version is not supported")
        if set(payload) != {"schema_version", "datasets"}:
            raise RegistryFormatError(
                "Versioned registry must contain only schema_version and datasets"
            )
        entries = payload["datasets"]
        if not isinstance(entries, list):
            raise RegistryFormatError("Versioned registry datasets must be a list")
    elif isinstance(payload, dict) and "datasets" in payload:
        entries = payload["datasets"]
        is_legacy = True
        if not isinstance(entries, list):
            raise RegistryFormatError("Legacy registry datasets must be a list")
    else:
        raise RegistryFormatError(
            "Registry JSON must use the versioned schema or a supported legacy shape"
        )

    records: list[DatasetRecord] = []
    dataset_ids: set[str] = set()
    for index, entry in enumerate(entries):
        record = (
            _parse_legacy_record(entry, index)
            if is_legacy
            else _parse_versioned_record(entry)
        )
        dataset_id = record.metadata.dataset_id
        if dataset_id in dataset_ids:
            raise RegistryFormatError(f"Registry contains duplicate dataset_id {dataset_id!r}")
        dataset_ids.add(dataset_id)
        records.append(record)

    return tuple(records)


def load_registry(settings: Settings) -> tuple[DatasetRecord, ...]:
    """Load and validate registry records from ``settings.data_dir/registry.json``.

    A missing registry file (including a missing data directory) returns an
    immutable empty tuple. Malformed or unsupported registry files raise
    ``RegistryFormatError``; invalid metadata or storage paths raise
    ``DataContractError``. Legacy list and ``{"datasets": [...]}`` shapes are
    accepted only when every entry includes a valid storage path. The loader
    never writes or migrates a registry.
    """
    registry_path = resolve_storage_path(settings, PurePosixPath(REGISTRY_FILENAME))
    if registry_path.is_dir():
        raise RegistryFormatError("Registry path must identify a file")

    try:
        text = registry_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ()
    except UnicodeDecodeError:
        raise RegistryFormatError("Registry file must contain UTF-8 JSON") from None

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise RegistryFormatError("Registry file contains malformed JSON") from None

    records = _parse_registry_payload(payload)
    for record in records:
        resolve_storage_path(settings, record)
    return records


def _validate_record(record: DatasetRecord) -> None:
    """Recheck public input contracts at the service boundary."""
    if not isinstance(record, DatasetRecord):
        raise DataContractError("record must be a DatasetRecord instance")
    if not isinstance(record.metadata, DatasetMetadata):
        raise DataContractError("metadata must be a DatasetMetadata instance")
    # Frozen dataclasses can still be forged or mutated through low-level APIs.
    record.metadata.__post_init__()
    _validate_storage_path(record.storage_path)


def _metadata_payload(metadata: DatasetMetadata) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dataset_id": metadata.dataset_id,
        "name": metadata.name,
        "industry": metadata.industry,
        "created_at": metadata.created_at.isoformat(),
    }
    if metadata.source is not None:
        payload["source"] = metadata.source
    return payload


def _write_registry(settings: Settings, records: tuple[DatasetRecord, ...]) -> None:
    """Atomically persist a complete versioned registry document."""
    destination = resolve_storage_path(settings, PurePosixPath(REGISTRY_FILENAME))
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "datasets": [
            {
                "metadata": _metadata_payload(record.metadata),
                "storage_path": str(record.storage_path),
            }
            for record in records
        ],
    }
    serialized = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=destination.parent,
            prefix=f".{REGISTRY_FILENAME}.", suffix=".tmp", delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
    except BaseException as write_error:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                write_error.add_note(
                    f"Temporary registry file cleanup also failed: {cleanup_error}"
                )
        raise


def _mutable_registry_records(
    settings: Settings, *, allow_missing: bool
) -> tuple[DatasetRecord, ...]:
    destination = resolve_storage_path(settings, PurePosixPath(REGISTRY_FILENAME))
    if not destination.exists():
        if allow_missing:
            return ()
        raise RegistryFormatError("Cannot update a dataset because the registry does not exist")
    if destination.is_dir():
        raise RegistryFormatError("Registry path must identify a file")
    try:
        payload = json.loads(destination.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        raise RegistryFormatError("Registry file must contain UTF-8 JSON") from None
    except json.JSONDecodeError:
        # Delegate to the established loader for its consistent public error.
        return load_registry(settings)
    if not isinstance(payload, dict) or "schema_version" not in payload:
        raise RegistryFormatError(
            "Cannot mutate a legacy registry; explicit migration is required first"
        )
    return load_registry(settings)


def register_dataset(settings: Settings, record: DatasetRecord) -> DatasetRecord:
    """Validate, append, and atomically persist a new dataset record."""
    _validate_record(record)
    resolve_storage_path(settings, record)
    records = _mutable_registry_records(settings, allow_missing=True)
    dataset_id = record.metadata.dataset_id
    if any(existing.metadata.dataset_id == dataset_id for existing in records):
        raise DataContractError(f"dataset_id {dataset_id!r} is already registered")
    _write_registry(settings, (*records, record))
    return record


def update_dataset(settings: Settings, record: DatasetRecord) -> DatasetRecord:
    """Replace an existing record by its immutable dataset identity."""
    _validate_record(record)
    resolve_storage_path(settings, record)
    records = _mutable_registry_records(settings, allow_missing=False)
    dataset_id = record.metadata.dataset_id
    if not any(existing.metadata.dataset_id == dataset_id for existing in records):
        raise DataContractError(f"dataset_id {dataset_id!r} is not registered")
    updated = tuple(
        record if existing.metadata.dataset_id == dataset_id else existing
        for existing in records
    )
    _write_registry(settings, updated)
    return record
