# MarketMind

MarketMind is a modular, multi-industry business intelligence and data science
platform. This repository currently contains its Python foundation only.

## Development setup

Python 3.11 or newer is required.

```console
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## Foundation modules

- `marketmind.config`: immutable application settings loaded from environment
  variables with validation and predictable defaults.
- `marketmind.errors`: stable exception types for callers and API boundaries.
- `marketmind.logging`: opt-in standard-library logging setup with a consistent
  format and no import-time side effects.
- `marketmind.contracts`: small shared data contracts for dataset metadata.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for scope and progress. This is not
yet an analytics engine, ingestion service, API, or industry-specific product.
