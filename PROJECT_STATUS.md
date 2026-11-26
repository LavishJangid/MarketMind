# MarketMind Project Status

## Current milestone: Milestone 2 — Dataset Registry & Ingestion

Milestone 1 (Foundation) and the Presentation Layer Shell & Overview are complete.
MM-021 adds the backend dataset record value object. Registry persistence,
filesystem resolution, and ingestion have not been implemented.

### Completed

#### Milestone 1 — Foundation (preserved unchanged)

- Established a `src`-based Python package and pytest/Ruff configuration.
- Added immutable settings (`marketmind.config.Settings`), shared exceptions
  (`marketmind.errors`), explicit logging (`marketmind.logging`), and the
  timezone-aware `DatasetMetadata` contract (`marketmind.contracts`).

#### Presentation Layer — Shell & Overview

- Added `plotly>=5.24` and `streamlit>=1.39` to `pyproject.toml` and installed
  them in the active Python environment (`streamlit 1.67.0`, `plotly 7.2.0`).
- Added `app` to Ruff's source configuration and first-party isort settings, and
  added `.` to pytest `pythonpath` in `pyproject.toml`.
- Added read-only registry inspection in `app/registry.py` using
  `Settings.data_dir` (`registry.json`) and validating entries with
  `marketmind.contracts.DatasetMetadata`. Missing registry files are treated as
  valid empty states; malformed or contract-violating files surface structured
  errors.
- Added restrained visual tokens and a Plotly-compatible layout helper in
  `app/ui/theme.py`.
- Added reusable UI components in `app/ui/components.py`: page header, KPI
  tiles, empty state, and error state.
- Added the Overview page (`app/views/overview.py`) presenting the platform
  introduction, live registry status KPIs, and industry availability cards for
  Retail & E-commerce, Banking & Marketing, and Hospitality without fabricated
  metrics or sample datasets.
- Added the Streamlit entry point and navigation shell (`app/main.py`) with
  MarketMind branding, sidebar navigation, configuration error handling, and
  explicit pending placeholders for industry analytics pages.
- Added registry and Streamlit `AppTest` UI tests in `tests/test_registry.py`
  and `tests/test_ui_app.py`.

#### Milestone 2 — Dataset Registry & Ingestion

- **MM-021 — Backend Dataset Record & Registry API:** added the immutable
  `marketmind.registry.DatasetRecord`, composing the existing
  `DatasetMetadata` with a portable relative `PurePosixPath`. The model rejects
  missing, absolute, traversing, and non-portable path shapes while leaving
  metadata field validation to the existing contract. It performs no registry
  I/O or filesystem resolution.
- Added focused model tests in `tests/test_dataset_record.py` for construction,
  immutability, path validation, and delegation to `DatasetMetadata` validation.
- No registry service methods or dependencies were added in MM-021.
- **MM-022 has not started.**

### Verification

- `python -m compileall -q src app tests`: passed (exit code 0).
- `python -m ruff check .`: passed (exit code 0).
- `python -m pytest -v`, with PowerShell `TEMP` and `TMP` pointed to a temporary
  directory under the writable workspace: 77 passed, 1 skipped, 0 failures, and
  0 setup errors (exit code 0). The symlink escape test was skipped because this
  environment does not permit symlink creation. Pytest emitted a cache warning
  because `.pytest_cache` is not writable here.
- `git diff --check`: passed.
- Verification used Python 3.13.7. Python 3.12 is not installed in this
  environment and was not runtime-tested.
- The presentation-layer Streamlit startup and HTTP health checks were verified
  previously; they were not rerun for MM-021.

### Remaining work

- MM-022 path resolution has not started and requires approval before work begins.
- Subsequent MM-023 to MM-040 registry and ingestion work remains pending.
