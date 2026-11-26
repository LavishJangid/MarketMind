from datetime import UTC, datetime

import pytest

from marketmind.contracts import DatasetMetadata
from marketmind.errors import DataContractError


def test_dataset_metadata_accepts_valid_values() -> None:
    metadata = DatasetMetadata(
        dataset_id="sales-2026",
        name="Sales",
        industry="retail",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        source="warehouse",
    )
    assert metadata.industry == "retail"


def test_dataset_metadata_requires_timezone() -> None:
    with pytest.raises(DataContractError, match="timezone"):
        DatasetMetadata("sales", "Sales", "retail", datetime(2026, 1, 1))


def test_dataset_metadata_rejects_blank_required_fields() -> None:
    with pytest.raises(DataContractError, match="name"):
        DatasetMetadata("sales", "  ", "retail", datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_id", 1),
        ("name", None),
        ("industry", []),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("source", 1),
    ],
)
def test_dataset_metadata_rejects_invalid_runtime_types(field: str, value: object) -> None:
    values = {
        "dataset_id": "sales",
        "name": "Sales",
        "industry": "retail",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "source": None,
    }
    values[field] = value
    with pytest.raises(DataContractError, match=field):
        DatasetMetadata(**values)  # type: ignore[arg-type]
