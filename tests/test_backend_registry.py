from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

import marketmind.registry as registry_api
from marketmind.config import Settings
from marketmind.errors import DataContractError
from marketmind.registry import (
    REGISTRY_FILENAME,
    REGISTRY_SCHEMA_VERSION,
    DatasetRecord,
    RegistryFormatError,
    load_registry,
)


def _metadata(dataset_id: str = "dataset-001") -> dict[str, object]:
    return {
        "dataset_id": dataset_id,
        "name": "Orders",
        "industry": "retail",
        "created_at": "2026-01-01T00:00:00+00:00",
        "source": "test fixture",
    }


def _versioned_record(
    dataset_id: str = "dataset-001",
    storage_path: str = "datasets/dataset-001/data.parquet",
) -> dict[str, object]:
    return {
        "metadata": _metadata(dataset_id),
        "storage_path": storage_path,
    }


def _write_registry(data_dir: Path, payload: Any) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    registry_path = data_dir / REGISTRY_FILENAME
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    return registry_path


def _versioned_payload(*records: dict[str, object]) -> dict[str, object]:
    return {"schema_version": REGISTRY_SCHEMA_VERSION, "datasets": list(records)}


def test_load_registry_reads_versioned_schema_and_lists_immutable_records(
    tmp_path: Path,
) -> None:
    _write_registry(tmp_path, _versioned_payload(_versioned_record()))

    records = load_registry(Settings(data_dir=tmp_path))

    assert isinstance(records, tuple)
    assert len(records) == 1
    assert isinstance(records[0], DatasetRecord)
    assert records[0].metadata.dataset_id == "dataset-001"
    assert records[0].storage_path == PurePosixPath("datasets/dataset-001/data.parquet")
    assert records[0].metadata.created_at == datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(TypeError):
        records[0] = records[0]  # type: ignore[index]


def test_load_registry_accepts_empty_versioned_registry(tmp_path: Path) -> None:
    _write_registry(tmp_path, _versioned_payload())

    assert load_registry(Settings(data_dir=tmp_path)) == ()


def test_missing_registry_returns_empty_without_creating_data_directory(
    tmp_path: Path,
) -> None:
    missing_data_dir = tmp_path / "not-created"

    assert load_registry(Settings(data_dir=missing_data_dir)) == ()
    assert not missing_data_dir.exists()


@pytest.mark.parametrize(
    "legacy_payload",
    [
        [_metadata() | {"storage_path": "datasets/dataset-001/data.parquet"}],
        {"datasets": [_metadata() | {"storage_path": "datasets/dataset-001/data.parquet"}]},
    ],
)
def test_load_registry_accepts_mappable_legacy_shapes(
    tmp_path: Path,
    legacy_payload: object,
) -> None:
    registry_path = _write_registry(tmp_path, legacy_payload)
    original_bytes = registry_path.read_bytes()

    records = load_registry(Settings(data_dir=tmp_path))

    assert len(records) == 1
    assert records[0].metadata.dataset_id == "dataset-001"
    assert records[0].storage_path == PurePosixPath("datasets/dataset-001/data.parquet")
    assert registry_path.read_bytes() == original_bytes


@pytest.mark.parametrize(
    "legacy_payload",
    [
        [_metadata()],
        {"datasets": [_metadata()]},
    ],
)
def test_legacy_records_without_storage_path_are_not_invented(
    tmp_path: Path,
    legacy_payload: object,
) -> None:
    _write_registry(tmp_path, legacy_payload)

    with pytest.raises(RegistryFormatError, match="cannot be mapped.*without inventing a path"):
        load_registry(Settings(data_dir=tmp_path))


@pytest.mark.parametrize(
    "invalid_record",
    [
        _metadata("") | {"storage_path": "datasets/data.parquet"},
        _metadata() | {"storage_path": "../outside.parquet"},
    ],
)
@pytest.mark.parametrize("as_envelope", [False, True])
def test_legacy_invalid_metadata_or_path_is_rejected(
    tmp_path: Path,
    invalid_record: dict[str, object],
    as_envelope: bool,
) -> None:
    payload: object = {"datasets": [invalid_record]} if as_envelope else [invalid_record]
    _write_registry(tmp_path, payload)

    with pytest.raises(DataContractError):
        load_registry(Settings(data_dir=tmp_path))


@pytest.mark.parametrize("as_envelope", [False, True])
def test_mixed_legacy_records_are_rejected_as_a_whole(
    tmp_path: Path,
    as_envelope: bool,
) -> None:
    valid_record = _metadata() | {"storage_path": "datasets/data.parquet"}
    invalid_record = _metadata("") | {"storage_path": "datasets/invalid.parquet"}
    entries = [valid_record, invalid_record]
    payload: object = {"datasets": entries} if as_envelope else entries
    registry_path = _write_registry(tmp_path, payload)
    original_bytes = registry_path.read_bytes()

    with pytest.raises(DataContractError):
        load_registry(Settings(data_dir=tmp_path))

    assert registry_path.read_bytes() == original_bytes


def test_legacy_empty_shapes_are_safe_to_read(tmp_path: Path) -> None:
    for legacy_payload in ([], {"datasets": []}):
        data_dir = tmp_path / str(len(legacy_payload))
        _write_registry(data_dir, legacy_payload)
        assert load_registry(Settings(data_dir=data_dir)) == ()


def test_malformed_json_raises_registry_format_error(tmp_path: Path) -> None:
    data_dir = tmp_path
    data_dir.mkdir(exist_ok=True)
    (data_dir / REGISTRY_FILENAME).write_text("{broken", encoding="utf-8")

    with pytest.raises(RegistryFormatError, match="malformed JSON"):
        load_registry(Settings(data_dir=data_dir))


@pytest.mark.parametrize("payload", [None, 42, "registry", {"other": []}])
def test_invalid_top_level_structure_raises_registry_format_error(
    tmp_path: Path,
    payload: object,
) -> None:
    _write_registry(tmp_path, payload)

    with pytest.raises(RegistryFormatError, match="versioned schema|legacy shape"):
        load_registry(Settings(data_dir=tmp_path))


@pytest.mark.parametrize("version", [0, 2, "1", True])
def test_unsupported_or_invalid_schema_version_is_rejected(
    tmp_path: Path,
    version: object,
) -> None:
    _write_registry(tmp_path, {"schema_version": version, "datasets": []})

    with pytest.raises(RegistryFormatError, match="schema version"):
        load_registry(Settings(data_dir=tmp_path))


def test_invalid_metadata_uses_existing_dataset_contract_error(tmp_path: Path) -> None:
    invalid_record = _versioned_record()
    invalid_record["metadata"] = _metadata("")
    _write_registry(tmp_path, _versioned_payload(invalid_record))

    with pytest.raises(DataContractError, match="dataset_id"):
        load_registry(Settings(data_dir=tmp_path))


def test_invalid_storage_path_uses_existing_data_contract_error(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        _versioned_payload(_versioned_record(storage_path="../outside.parquet")),
    )

    with pytest.raises(DataContractError, match="traversal"):
        load_registry(Settings(data_dir=tmp_path))


def test_duplicate_dataset_ids_are_rejected(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        _versioned_payload(
            _versioned_record(storage_path="datasets/one.parquet"),
            _versioned_record(storage_path="datasets/two.parquet"),
        ),
    )

    with pytest.raises(RegistryFormatError, match="duplicate dataset_id"):
        load_registry(Settings(data_dir=tmp_path))


def test_identical_file_contents_with_distinct_ids_are_allowed(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    first_path = data_root / "datasets" / "first.parquet"
    second_path = data_root / "datasets" / "second.parquet"
    first_path.parent.mkdir(parents=True)
    first_path.write_bytes(b"same temporary test content")
    second_path.write_bytes(b"same temporary test content")
    _write_registry(
        data_root,
        _versioned_payload(
            _versioned_record("dataset-001", "datasets/first.parquet"),
            _versioned_record("dataset-002", "datasets/second.parquet"),
        ),
    )

    records = load_registry(Settings(data_dir=data_root))

    assert [record.metadata.dataset_id for record in records] == [
        "dataset-001",
        "dataset-002",
    ]


def test_registry_read_errors_are_not_treated_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = _write_registry(tmp_path, _versioned_payload())
    original_read_text = Path.read_text

    def deny_registry_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == registry_path:
            raise PermissionError("registry access denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_registry_read)

    with pytest.raises(PermissionError, match="registry access denied"):
        load_registry(Settings(data_dir=tmp_path))


def test_load_registry_uses_shared_resolver_for_registry_and_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _versioned_record()
    _write_registry(tmp_path, _versioned_payload(record))
    original_resolver = registry_api.resolve_storage_path
    resolved_inputs: list[PurePosixPath] = []

    def recording_resolver(
        settings: Settings,
        record_or_path: DatasetRecord | PurePosixPath,
    ) -> Path:
        path = (
            record_or_path.storage_path
            if isinstance(record_or_path, DatasetRecord)
            else record_or_path
        )
        resolved_inputs.append(path)
        return original_resolver(settings, record_or_path)

    monkeypatch.setattr(registry_api, "resolve_storage_path", recording_resolver)

    load_registry(Settings(data_dir=tmp_path))

    assert resolved_inputs == [
        PurePosixPath(REGISTRY_FILENAME),
        PurePosixPath("datasets/dataset-001/data.parquet"),
    ]
