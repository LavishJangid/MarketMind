from __future__ import annotations

import errno
import json
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pytest

import marketmind.registry as registry_api
from marketmind.config import Settings
from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError
from marketmind.registry import DatasetRecord, RegistryFormatError, load_registry


def _create_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except NotImplementedError:
        pytest.skip("This operating system does not support symlinks")
    except OSError as exc:
        unsupported_errnos = {
            errno.EACCES,
            errno.EPERM,
            getattr(errno, "ENOTSUP", errno.EPERM),
            getattr(errno, "EOPNOTSUPP", errno.EPERM),
        }
        unsupported_winerrors = {50, 1314}
        if (
            exc.errno in unsupported_errnos
            or getattr(exc, "winerror", None) in unsupported_winerrors
        ):
            pytest.skip(f"Environment prevents symlink creation: {exc}")
        raise


def _record(
    dataset_id: str = "dataset-001",
    path: str = "datasets/a.parquet",
    name: str = "Orders",
) -> DatasetRecord:
    return DatasetRecord(
        DatasetMetadata(dataset_id, name, "retail", datetime(2026, 1, 1, tzinfo=UTC)),
        PurePosixPath(path),
    )


def _metadata(
    dataset_id: str = "dataset-001", name: str = "Renamed Orders"
) -> DatasetMetadata:
    return DatasetMetadata(
        dataset_id,
        name,
        "retail",
        datetime(2026, 2, 1, tzinfo=UTC),
        "updated source",
    )


def test_register_missing_registry_and_preserve_duplicate_content(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "nested" / "data")
    first = _record()
    second = _record("dataset-002")

    assert registry_api.register_dataset(settings, first) is first
    registry_api.register_dataset(settings, second)

    assert load_registry(settings) == (first, second)
    assert (settings.data_dir / "datasets").exists() is False
    assert json.loads((settings.data_dir / "registry.json").read_text())[
        "schema_version"
    ] == 1


def test_register_rejects_duplicate_and_invalid_record(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())
    with pytest.raises(DataContractError, match="already registered"):
        registry_api.register_dataset(settings, _record(path="datasets/other.parquet"))
    with pytest.raises(DataContractError, match="DatasetRecord"):
        registry_api.register_dataset(settings, object())  # type: ignore[arg-type]


def test_update_replaces_target_and_preserves_other_records(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    original, other = _record(), _record("dataset-002")
    registry_api.register_dataset(settings, original)
    registry_api.register_dataset(settings, other)
    replacement = _record(path="datasets/new.parquet", name="Updated Orders")

    assert registry_api.update_dataset(settings, replacement) is replacement
    assert load_registry(settings) == (replacement, other)


def test_update_rejects_missing_registry_and_unknown_id(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    with pytest.raises(RegistryFormatError, match="does not exist"):
        registry_api.update_dataset(settings, _record())
    registry_api.register_dataset(settings, _record())
    with pytest.raises(DataContractError, match="not registered"):
        registry_api.update_dataset(settings, _record("unknown"))


def test_update_dataset_metadata_preserves_identity_path_and_record_order(
    tmp_path: Path,
) -> None:
    settings = Settings(data_dir=tmp_path)
    records = (
        _record("dataset-001", "datasets/original.parquet"),
        _record("dataset-002", "datasets/second.parquet"),
        _record("dataset-003", "datasets/third.parquet"),
    )
    for record in records:
        registry_api.register_dataset(settings, record)

    returned = registry_api.update_dataset_metadata(
        settings, "dataset-002", _metadata("dataset-002")
    )
    persisted = load_registry(settings)

    assert returned.metadata == _metadata("dataset-002")
    assert returned.metadata.dataset_id == "dataset-002"
    assert returned.storage_path == records[1].storage_path
    assert [record.metadata.dataset_id for record in persisted] == [
        "dataset-001",
        "dataset-002",
        "dataset-003",
    ]
    assert persisted[0] == records[0]
    assert persisted[1].metadata == returned.metadata
    assert persisted[1].storage_path == records[1].storage_path
    assert persisted[2] == records[2]


def test_update_dataset_metadata_rejects_invalid_or_mismatched_metadata(
    tmp_path: Path,
) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())
    invalid_metadata = object.__new__(DatasetMetadata)
    object.__setattr__(invalid_metadata, "dataset_id", "dataset-001")
    object.__setattr__(invalid_metadata, "name", " ")
    object.__setattr__(invalid_metadata, "industry", "retail")
    object.__setattr__(invalid_metadata, "created_at", datetime(2026, 2, 1, tzinfo=UTC))
    object.__setattr__(invalid_metadata, "source", None)

    with pytest.raises(DataContractError, match="name cannot be empty"):
        registry_api.update_dataset_metadata(settings, "dataset-001", invalid_metadata)
    with pytest.raises(DataContractError, match="must match"):
        registry_api.update_dataset_metadata(settings, "dataset-001", _metadata("another-id"))


def test_update_dataset_metadata_rejects_unknown_id(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())

    with pytest.raises(DataContractError, match="not registered"):
        registry_api.update_dataset_metadata(settings, "unknown", _metadata("unknown"))


def test_update_dataset_metadata_write_failure_preserves_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())
    registry = tmp_path / "registry.json"
    before = registry.read_bytes()
    monkeypatch.setattr(
        os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(OSError, match="replace failed"):
        registry_api.update_dataset_metadata(
            settings, "dataset-001", _metadata("dataset-001")
        )

    assert registry.read_bytes() == before
    assert list(tmp_path.glob(".registry.json.*.tmp")) == []


@pytest.mark.parametrize("legacy", [[{"dataset_id": "x"}], {"datasets": []}])
def test_mutations_reject_legacy_without_modifying_bytes(tmp_path: Path, legacy: object) -> None:
    path = tmp_path / "registry.json"
    original = json.dumps(legacy).encode()
    path.write_bytes(original)
    with pytest.raises(RegistryFormatError, match="legacy registry"):
        registry_api.register_dataset(Settings(data_dir=tmp_path), _record())
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "original",
    [b"{bad", b'{"schema_version": 99, "datasets": []}',
     b'{"schema_version": 1, "datasets": [{"metadata": {}, "storage_path": "x"}]}'],
)
def test_mutations_reject_corrupt_or_invalid_registry_unchanged(
    tmp_path: Path, original: bytes
) -> None:
    path = tmp_path / "registry.json"
    path.write_bytes(original)
    with pytest.raises((RegistryFormatError, DataContractError)):
        registry_api.register_dataset(Settings(data_dir=tmp_path), _record())
    assert path.read_bytes() == original


@pytest.mark.parametrize("failure", ["write", "flush", "fsync", "replace"])
def test_atomic_write_failure_preserves_registry_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())
    registry = tmp_path / "registry.json"
    before = registry.read_bytes()
    if failure == "fsync":
        monkeypatch.setattr(os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError("sync failed")))
    elif failure == "replace":
        monkeypatch.setattr(
            os,
            "replace",
            lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
        )
    else:
        original_write = registry_api.tempfile.NamedTemporaryFile

        class BrokenWriter:
            def __enter__(self):
                self.file = original_write(
                    mode="w", encoding="utf-8", newline="\n", dir=tmp_path,
                    prefix=".registry.json.", suffix=".tmp", delete=False,
                )
                self.name = self.file.name
                return self

            def write(self, _text: str) -> int:
                if failure == "write":
                    raise OSError("write failed")
                return self.file.write(_text)

            def flush(self) -> None:
                if failure == "flush":
                    raise OSError("flush failed")
                self.file.flush()

            def fileno(self) -> int:
                return self.file.fileno()

            def __exit__(self, *_args: object) -> None:
                self.file.close()

        monkeypatch.setattr(
            registry_api.tempfile,
            "NamedTemporaryFile",
            lambda **_kwargs: BrokenWriter(),
        )
    expected_messages = {
        "write": "write failed",
        "flush": "flush failed",
        "fsync": "sync failed",
        "replace": "replace failed",
    }
    with pytest.raises(OSError, match=expected_messages[failure]):
        registry_api.register_dataset(settings, _record("dataset-002"))
    assert registry.read_bytes() == before
    assert list(tmp_path.glob(".registry.json.*.tmp")) == []


def test_temp_creation_failure_preserves_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())
    registry = tmp_path / "registry.json"
    before = registry.read_bytes()
    monkeypatch.setattr(
        registry_api.tempfile, "NamedTemporaryFile",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("create failed")),
    )
    with pytest.raises(OSError, match="create failed"):
        registry_api.register_dataset(settings, _record("dataset-002"))
    assert registry.read_bytes() == before


def test_temporary_file_is_created_in_registry_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(data_dir=tmp_path / "nested" / "data")
    original = registry_api.tempfile.NamedTemporaryFile
    observed: list[Path] = []

    def record_temp_directory(**kwargs: object):
        observed.append(Path(kwargs["dir"]))  # type: ignore[arg-type]
        return original(**kwargs)

    monkeypatch.setattr(registry_api.tempfile, "NamedTemporaryFile", record_temp_directory)
    registry_api.register_dataset(settings, _record())

    assert observed == [settings.data_dir.resolve()]
    assert not (settings.data_dir / "datasets").exists()


@pytest.mark.parametrize("operation", ["register", "update"])
def test_mutations_reject_storage_path_symlink_to_outside(
    tmp_path: Path, operation: str
) -> None:
    data_dir = tmp_path / "data"
    outside_dir = tmp_path / "outside"
    data_dir.mkdir()
    outside_dir.mkdir()
    link = data_dir / "linked"
    _create_symlink_or_skip(link, outside_dir)
    settings = Settings(data_dir=data_dir)
    registry = data_dir / "registry.json"

    if operation == "update":
        registry_api.register_dataset(settings, _record())
        original_registry = registry.read_bytes()
    else:
        original_registry = None

    invalid_record = _record(path="linked/new.parquet")
    method = (
        registry_api.register_dataset
        if operation == "register"
        else registry_api.update_dataset
    )
    with pytest.raises(DataContractError, match="outside the configured data root"):
        method(settings, invalid_record)

    if original_registry is None:
        assert not registry.exists()
    else:
        assert registry.read_bytes() == original_registry
    assert list(outside_dir.iterdir()) == []
    assert list(data_dir.glob("linked/new.parquet")) == []


def test_cleanup_failure_does_not_hide_primary_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(data_dir=tmp_path)
    registry_api.register_dataset(settings, _record())
    registry = tmp_path / "registry.json"
    before = registry.read_bytes()
    temporary_paths: list[str] = []
    original_temp = registry_api.tempfile.NamedTemporaryFile
    original_unlink = os.unlink

    def record_temp(**kwargs: object):
        temporary_file = original_temp(**kwargs)
        temporary_paths.append(temporary_file.name)
        return temporary_file

    def fail_sync(_fd: int) -> None:
        raise OSError("primary sync failure")

    def fail_temp_cleanup(path: str, *args: object, **kwargs: object) -> None:
        if temporary_paths and path == temporary_paths[0]:
            raise PermissionError("cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(registry_api.tempfile, "NamedTemporaryFile", record_temp)
    monkeypatch.setattr(os, "fsync", fail_sync)
    monkeypatch.setattr(os, "unlink", fail_temp_cleanup)

    with pytest.raises(OSError, match="primary sync failure") as exc_info:
        registry_api.register_dataset(settings, _record("dataset-002"))

    assert any("cleanup failure" in note for note in exc_info.value.__notes__)
    assert registry.read_bytes() == before
    assert len(temporary_paths) == 1
    monkeypatch.undo()
    Path(temporary_paths[0]).unlink()
