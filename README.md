# MiniPortfolioAnalysis

## Nightbatch Runner

The central nightbatch orchestrator is now:

- `src/nightbatch/run_full_nightbatch.py`

This script runs:

1. FX update (`src/nightbatch/run_fx_update.py`)
2. iShares price update (`src/nightbatch/ishares_importer.py`)

## GitHub Actions

The scheduled workflow is configured in:

- `.github/workflows/full_nightbatch.yml`

It executes:

```bash
python src/nightbatch/run_full_nightbatch.py
```

## Local test

Run the full nightbatch locally with:

```bash
python src/nightbatch/run_full_nightbatch.py
```
