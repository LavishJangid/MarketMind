from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest

from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError
from marketmind.registry import DatasetRecord


def _metadata() -> DatasetMetadata:
    return DatasetMetadata(
        dataset_id="dataset-001",
        name="Orders",
        industry="retail",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="warehouse",
    )


def test_dataset_record_accepts_metadata_and_relative_storage_path() -> None:
    metadata = _metadata()

    record = DatasetRecord(metadata, PurePosixPath("datasets/dataset-001/data.parquet"))

    assert record.metadata is metadata
    assert record.storage_path == PurePosixPath("datasets/dataset-001/data.parquet")
    assert record.metadata.dataset_id == "dataset-001"


def test_dataset_record_is_immutable() -> None:
    record = DatasetRecord(_metadata(), PurePosixPath("datasets/dataset-001/data.parquet"))

    with pytest.raises(FrozenInstanceError):
        record.storage_path = PurePosixPath("other/data.parquet")  # type: ignore[misc]


def test_dataset_record_requires_storage_path() -> None:
    with pytest.raises(TypeError, match="storage_path"):
        DatasetRecord(metadata=_metadata())  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "storage_path",
    [None, "", PurePosixPath("."), PurePosixPath("\0")],
)
def test_dataset_record_rejects_missing_or_invalid_storage_path(
    storage_path: object,
) -> None:
    with pytest.raises(DataContractError, match="storage_path"):
        DatasetRecord(_metadata(), storage_path)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "storage_path",
    [
        PurePosixPath("/var/marketmind/data.parquet"),
        PurePosixPath("//server/share/data.parquet"),
    ],
)
def test_dataset_record_rejects_absolute_storage_path(storage_path: PurePosixPath) -> None:
    with pytest.raises(DataContractError, match="relative path"):
        DatasetRecord(_metadata(), storage_path)


@pytest.mark.parametrize(
    "storage_path",
    [PurePosixPath("../outside.parquet"), PurePosixPath("datasets/../../outside.parquet")],
)
def test_dataset_record_rejects_parent_traversal(storage_path: PurePosixPath) -> None:
    with pytest.raises(DataContractError, match="traversal"):
        DatasetRecord(_metadata(), storage_path)


@pytest.mark.parametrize(
    "storage_path",
    [PurePosixPath(r"datasets\data.parquet"), PurePosixPath("C:/data.parquet")],
)
def test_dataset_record_rejects_non_portable_path_shapes(storage_path: PurePosixPath) -> None:
    with pytest.raises(DataContractError, match="relative path"):
        DatasetRecord(_metadata(), storage_path)


def test_dataset_metadata_remains_authoritative_for_identity_validation() -> None:
    with pytest.raises(DataContractError, match="dataset_id"):
        DatasetMetadata(
            dataset_id=" ",
            name="Orders",
            industry="retail",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_dataset_record_requires_existing_metadata_contract() -> None:
    with pytest.raises(DataContractError, match="DatasetMetadata"):
        DatasetRecord(object(), PurePosixPath("datasets/dataset-001/data.parquet"))  # type: ignore[arg-type]
