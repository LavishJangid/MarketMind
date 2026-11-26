from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from app.ui.theme import plotly_layout_defaults

APP_PATH = str(Path(__file__).resolve().parents[1] / "app" / "main.py")


def test_overview_renders_empty_state_without_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MARKETMIND_DATA_DIR", str(tmp_path / "missing_data"))
    monkeypatch.setenv("MARKETMIND_ENVIRONMENT", "testing")

    at = AppTest.from_file(APP_PATH).run()

    assert not at.exception
    assert any("Platform Overview" in title.value for title in at.title)
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Registered Datasets"] == "0"
    assert metrics["Active Industries"] == "0 / 3"
    assert metrics["Registry Status"] == "Not Initialized"

    subheaders = {s.value for s in at.subheader}
    assert {"Retail & E-commerce", "Banking & Marketing", "Hospitality"}.issubset(subheaders)


def test_overview_renders_registered_datasets_from_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(
            [
                {
                    "dataset_id": "hosp-2026",
                    "name": "Resort Bookings",
                    "industry": "hospitality",
                    "created_at": "2026-03-01T12:00:00+00:00",
                    "source": "pms",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MARKETMIND_DATA_DIR", str(tmp_path))

    at = AppTest.from_file(APP_PATH).run()

    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Registered Datasets"] == "1"
    assert metrics["Active Industries"] == "1 / 3"
    assert metrics["Registry Status"] == "Ready"
    assert any("Resort Bookings" in md.value for md in at.markdown)


def test_overview_renders_registry_error_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "registry.json").write_text("{malformed", encoding="utf-8")
    monkeypatch.setenv("MARKETMIND_DATA_DIR", str(tmp_path))

    at = AppTest.from_file(APP_PATH).run()

    assert not at.exception
    metrics = {metric.label: metric.value for metric in at.metric}
    assert metrics["Registry Status"] == "Error"
    assert any("Dataset Registry Could Not Be Loaded" in error.value for error in at.error)


def test_sidebar_navigation_shows_pending_industry_shell(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MARKETMIND_DATA_DIR", str(tmp_path))

    at = AppTest.from_file(APP_PATH).run()
    at.sidebar.radio(key="marketmind_navigation_page").set_value("Retail & E-commerce").run()

    assert not at.exception
    assert any("Retail & E-commerce" in title.value for title in at.title)
    assert any("Analytics Not Yet Implemented" in md.value for md in at.markdown)


def test_invalid_configuration_renders_error_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKETMIND_LOG_LEVEL", "TRACE")

    at = AppTest.from_file(APP_PATH).run()

    assert not at.exception
    assert len(at.error) == 1
    assert "Invalid Application Configuration" in at.error[0].value


def test_plotly_layout_defaults_build_valid_figure() -> None:
    fig = go.Figure(layout=plotly_layout_defaults(title="MarketMind Chart"))
    assert fig.layout.title.text == "MarketMind Chart"
    assert len(fig.layout.colorway) >= 3
