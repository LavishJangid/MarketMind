from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.registry import inspect_registry, normalize_industry_key
from marketmind.config import Settings


def test_missing_registry_is_valid_empty_state(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "nonexistent")
    status = inspect_registry(settings)

    assert status.registry_exists is False
    assert status.error is None
    assert status.datasets == ()
    assert status.total_datasets == 0
    assert status.active_industry_count == 0


def test_empty_registry_list_is_valid(tmp_path: Path) -> None:
    registry_file = tmp_path / "registry.json"
    registry_file.write_text("[]", encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.error is None
    assert status.total_datasets == 0
    assert status.active_industry_count == 0


def test_valid_custom_registry_filename_is_read_within_data_dir(tmp_path: Path) -> None:
    custom_registry = tmp_path / "metadata" / "datasets.json"
    custom_registry.parent.mkdir()
    custom_registry.write_text("[]", encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path), "metadata/datasets.json")

    assert status.registry_path == custom_registry.resolve()
    assert status.registry_exists is True
    assert status.error is None


@pytest.mark.parametrize("filename", ["../outside.json", "nested/../../outside.json"])
def test_registry_filename_rejects_parent_traversal(
    tmp_path: Path,
    filename: str,
) -> None:
    status = inspect_registry(Settings(data_dir=tmp_path), filename)

    assert status.registry_exists is False
    assert status.datasets == ()
    assert status.error is not None
    assert "inside data_dir" in status.error


def test_registry_filename_rejects_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-registry.json"
    outside.write_text("[]", encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path), str(outside))

    assert status.registry_exists is False
    assert status.error is not None
    assert "inside data_dir" in status.error


def test_registry_filename_rejects_symlink_that_resolves_outside_data_dir(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside-registry.json"
    outside.write_text("[]", encoding="utf-8")
    link = tmp_path / "registry-link.json"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError):
        pytest.skip("Symlink creation is unavailable in this environment")

    status = inspect_registry(Settings(data_dir=tmp_path), "registry-link.json")

    assert status.registry_exists is False
    assert status.error is not None
    assert "outside data_dir" in status.error


def test_valid_registry_parses_and_groups_industries(tmp_path: Path) -> None:
    registry_file = tmp_path / "registry.json"
    payload = {
        "datasets": [
            {
                "dataset_id": "ret-001",
                "name": "Online Orders Q1",
                "industry": "Retail & E-commerce",
                "created_at": "2026-02-01T10:30:00+00:00",
                "source": "warehouse",
            },
            {
                "dataset_id": "bnk-001",
                "name": "Term Deposit Campaign",
                "industry": "banking",
                "created_at": "2026-02-02T08:00:00Z",
                "source": None,
            },
        ]
    }
    registry_file.write_text(json.dumps(payload), encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.error is None
    assert status.total_datasets == 2
    assert status.active_industry_count == 2
    assert len(status.datasets_for_industry("retail")) == 1
    assert status.datasets_for_industry("retail")[0].dataset_id == "ret-001"
    assert len(status.datasets_for_industry("banking")) == 1
    assert status.datasets_for_industry("hospitality") == ()


def test_invalid_contract_in_registry_reports_error(tmp_path: Path) -> None:
    registry_file = tmp_path / "registry.json"
    payload = [
        {
            "dataset_id": "ret-bad",
            "name": "Missing Timezone",
            "industry": "retail",
            "created_at": "2026-02-01T10:30:00",
        }
    ]
    registry_file.write_text(json.dumps(payload), encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.error is not None
    assert "timezone" in status.error
    assert status.total_datasets == 0


def test_corrupt_json_registry_reports_error(tmp_path: Path) -> None:
    registry_file = tmp_path / "registry.json"
    registry_file.write_text("{not-valid-json", encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.error is not None
    assert status.datasets == ()


@pytest.mark.parametrize("payload", ['{"other": []}', '{"datasets": {}}', '42'])
def test_invalid_registry_structure_reports_error(tmp_path: Path, payload: str) -> None:
    (tmp_path / "registry.json").write_text(payload, encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.datasets == ()
    assert status.error is not None
    assert "must be a list" in status.error


@pytest.mark.parametrize(
    "record",
    [
        {
            "name": "Orders",
            "industry": "retail",
            "created_at": "2026-02-01T10:30:00+00:00",
        },
        {
            "dataset_id": "d1",
            "industry": "retail",
            "created_at": "2026-02-01T10:30:00+00:00",
        },
        {
            "dataset_id": "d1",
            "name": "Orders",
            "created_at": "2026-02-01T10:30:00+00:00",
        },
        {"dataset_id": "d1", "name": "Orders", "industry": "retail"},
        {
            "dataset_id": "d1",
            "name": "Orders",
            "industry": "retail",
            "created_at": "not-a-date",
        },
        {
            "dataset_id": "d1",
            "name": "Orders",
            "industry": "retail",
            "created_at": "2026-02-01T10:30:00+00:00",
            "source": 12,
        },
    ],
)
def test_invalid_dataset_metadata_reports_error(tmp_path: Path, record: dict[str, object]) -> None:
    (tmp_path / "registry.json").write_text(json.dumps([record]), encoding="utf-8")

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.datasets == ()
    assert status.error is not None


def test_registry_read_permission_error_is_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_file = tmp_path / "registry.json"
    registry_file.write_text("[]", encoding="utf-8")
    original_read_text = Path.read_text

    def deny_registry_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == registry_file:
            raise PermissionError("registry access denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny_registry_read)
    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.datasets == ()
    assert status.error == "registry access denied"


def test_directory_at_registry_path_reports_error(tmp_path: Path) -> None:
    (tmp_path / "registry.json").mkdir()

    status = inspect_registry(Settings(data_dir=tmp_path))

    assert status.registry_exists is True
    assert status.error is not None
    assert "directory" in status.error


def test_normalize_industry_key() -> None:
    assert normalize_industry_key("retail") == "retail"
    assert normalize_industry_key("  Retail & E-commerce ") == "retail"
    assert normalize_industry_key("BANKING") == "banking"
    assert normalize_industry_key("Hospitality") == "hospitality"
    assert normalize_industry_key("unknown-sector") is None
