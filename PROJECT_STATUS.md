# MarketMind Project Status

## Current milestone: Milestone 2 — Dataset Registry & Ingestion

Milestone 1 (Foundation) and the Presentation Layer Shell & Overview are complete.
MM-021 added the backend dataset record value object, MM-022 added safe storage
path resolution, and MM-023 added read-only backend registry loading/listing.
Registry writes and ingestion have not been implemented.

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

- **MM-022 — Storage Path Policy & Secure Filesystem Resolver:** added
  `resolve_storage_path` to `marketmind.registry`. It accepts a `DatasetRecord`
  or `PurePosixPath`, resolves against `Settings.data_dir`, follows existing
  symlinks, and checks containment with `Path.is_relative_to()`.
- A valid missing destination is returned as an absolute normalized path;
  neither the target nor missing parent directories are created. Callers can
  check `Path.exists()` to distinguish it from an existing target.
- Added resolver tests for existing and nested files, invalid/root paths,
  existing outside paths, missing targets, no mutation, and symlinks. Symlink
  skips are limited to unsupported platforms and known permission/support
  failures. The existing registry symlink test was given the same narrow skip
  policy.

- **MM-023 — Backend Registry Loading & Listing:** added `load_registry(settings)`,
  returning an immutable tuple of validated `DatasetRecord` values. The
  versioned JSON schema is `{"schema_version": 1, "datasets": [...]}`; each
  record contains nested `metadata` and a relative `storage_path`.
- Missing registry files return an empty tuple. Malformed JSON, invalid
  structure, unsupported versions, duplicate IDs, and unmappable legacy
  records raise `RegistryFormatError`. Metadata and path contract violations
  raise the existing `DataContractError`; filesystem read errors propagate as
  `OSError` rather than being treated as an empty registry.
- Legacy list and `{"datasets": [...]}` envelopes are read only when each
  record includes a valid `storage_path`. Existing UI legacy records without a
  storage path cannot be represented as `DatasetRecord` and are rejected
  explicitly; no path is fabricated and no file is rewritten.
- Registry file and dataset paths are checked through the MM-022
  `resolve_storage_path` resolver. Duplicate dataset IDs are rejected;
  identical file contents under different IDs are accepted. No dependencies or
  write operations were added.
- Added `tests/test_backend_registry.py` for versioned and legacy reads, error
  handling, duplicate behavior, resolver integration, and returned tuple
  immutability.
- MM-023 changed `src/marketmind/registry.py`, added
  `tests/test_backend_registry.py`, and updated `PROJECT_STATUS.md`.
- **MM-024 and later work has not started.**

### Verification

- `python -m compileall -q src app tests`: passed (exit code 0).
- `python -m ruff check .`: passed (exit code 0).
- `python -m pytest -v`, with PowerShell `TEMP` and `TMP` pointed to a temporary
  directory under the writable workspace: 109 passed, 4 skipped, 0 failures, and
  0 setup errors (exit code 0). All four symlink tests skipped because Windows
  returned `WinError 1314` (symlink privilege unavailable). Pytest emitted a
  cache warning because `.pytest_cache` is not writable here.
- `git diff --check`: passed.
- Verification used Python 3.13.7. Python 3.12 is not installed in this
  environment and was not runtime-tested.
- No dependencies were added for MM-021, MM-022, or MM-023.
- The presentation-layer Streamlit startup and HTTP health checks were verified
  previously; they were not rerun for MM-023.

### Remaining work

- MM-024 and later registry and ingestion work remains pending and requires
  approval before implementation.
