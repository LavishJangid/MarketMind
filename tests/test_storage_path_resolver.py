from __future__ import annotations

import errno
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pytest

from marketmind.config import Settings
from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError
from marketmind.registry import DatasetRecord, resolve_storage_path


def _record(storage_path: PurePosixPath) -> DatasetRecord:
    metadata = DatasetMetadata(
        dataset_id="dataset-001",
        name="Orders",
        industry="retail",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return DatasetRecord(metadata, storage_path)


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
        unsupported_winerrors = {50, 1314}  # not supported; symlink privilege unavailable
        if (
            exc.errno in unsupported_errnos
            or getattr(exc, "winerror", None) in unsupported_winerrors
        ):
            pytest.skip(f"Environment prevents symlink creation: {exc}")
        raise


def test_resolve_existing_relative_path_inside_data_root(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    target = data_root / "datasets" / "orders.parquet"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"parquet placeholder for resolver test")

    resolved = resolve_storage_path(
        Settings(data_dir=data_root),
        _record(PurePosixPath("datasets/orders.parquet")),
    )

    assert resolved == target.resolve()
    assert resolved.is_file()


def test_resolve_nested_path_from_relative_storage_path(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    target = data_root / "industry" / "retail" / "dataset-001" / "data.parquet"
    target.parent.mkdir(parents=True)
    target.touch()

    resolved = resolve_storage_path(
        Settings(data_dir=data_root),
        PurePosixPath("industry/retail/dataset-001/data.parquet"),
    )

    assert resolved == target.resolve()


@pytest.mark.parametrize(
    "storage_path",
    [
        PurePosixPath("/outside/data.parquet"),
        PurePosixPath("../outside/data.parquet"),
        PurePosixPath("datasets/../../outside/data.parquet"),
        PurePosixPath("."),
    ],
)
def test_resolver_rejects_absolute_traversal_and_root_paths(
    tmp_path: Path,
    storage_path: PurePosixPath,
) -> None:
    with pytest.raises(DataContractError):
        resolve_storage_path(Settings(data_dir=tmp_path / "data"), storage_path)


def test_existing_absolute_file_outside_data_root_is_rejected(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    outside_file = tmp_path / "outside.parquet"
    outside_file.write_bytes(b"outside")

    with pytest.raises(DataContractError, match="relative path"):
        resolve_storage_path(
            Settings(data_dir=data_root),
            PurePosixPath(outside_file.as_posix()),
        )


def test_missing_target_is_returned_without_creating_files_or_directories(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "not-created"
    missing_relative_path = PurePosixPath("datasets/new/data.parquet")

    resolved = resolve_storage_path(Settings(data_dir=data_root), missing_relative_path)

    assert resolved == (data_root / "datasets" / "new" / "data.parquet").resolve()
    assert not resolved.exists()
    assert not data_root.exists()


def test_resolver_does_not_mutate_existing_data_root(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    before = set(data_root.rglob("*"))

    resolve_storage_path(Settings(data_dir=data_root), PurePosixPath("new/deep/data.parquet"))

    assert set(data_root.rglob("*")) == before


def test_symlink_to_outside_data_root_is_rejected(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside_file = tmp_path / "outside.parquet"
    outside_file.write_bytes(b"outside")
    link = data_root / "outside-link.parquet"
    _create_symlink_or_skip(link, outside_file)

    with pytest.raises(DataContractError, match="outside the configured data root"):
        resolve_storage_path(Settings(data_dir=data_root), PurePosixPath("outside-link.parquet"))


def test_symlink_to_inside_data_root_resolves_to_target(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    target = data_root / "real" / "data.parquet"
    target.parent.mkdir(parents=True)
    target.touch()
    link = data_root / "alias.parquet"
    _create_symlink_or_skip(link, target)

    resolved = resolve_storage_path(Settings(data_dir=data_root), PurePosixPath("alias.parquet"))

    assert resolved == target.resolve()


def test_symlinked_data_root_is_resolved_as_the_trusted_root(tmp_path: Path) -> None:
    actual_root = tmp_path / "actual-data"
    actual_root.mkdir()
    configured_root = tmp_path / "configured-data"
    _create_symlink_or_skip(configured_root, actual_root)

    resolved = resolve_storage_path(
        Settings(data_dir=configured_root),
        PurePosixPath("datasets/new.parquet"),
    )

    assert resolved == (actual_root / "datasets" / "new.parquet").resolve()
