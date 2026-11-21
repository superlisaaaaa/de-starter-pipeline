# Nordlys Energy: a starter data-engineering pipeline

A small, complete data pipeline for learning **Git, GitHub and CI/CD**, and the
core principles a data engineer works by. Everything runs on your laptop for free.
There are no cloud accounts, no passwords and no real data: "Nordlys Energy" and all its customers are made up.

```
data/landing/<day>/*.csv           raw files arrive (like a source system export)
        │  python -m pipeline.extract_load
        ▼
bronze.*        raw, as received, + audit columns         (Python + DuckDB)
        │  dbt build
        ▼
silver.stg_*    cleaned, typed, deduplicated, tested       (dbt views)
        ▼
gold.*          business-ready facts, dimensions, marts    (dbt tables)
```

And around it, GitHub Actions:

| Workflow | When it runs | What it does |
|---|---|---|
| `ci.yml` | Every pull request | SQL lint → Python unit tests → run pipeline → dbt data tests |
| `cd.yml` | Merge to `main`, daily at 05:17 UTC, or by hand | Runs the pipeline, saves the warehouse, publishes dbt docs to GitHub Pages |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pipeline.extract_load    # load raw files into bronze
cd dbt_project
dbt build --profiles-dir .         # build + test silver and gold
cd ..
pytest -v                          # unit tests
```

**Start with [LEARNING_GUIDE.md](LEARNING_GUIDE.md).** It walks you through everything step by step.

## Project map

| Path | What it is |
|---|---|
| `pipeline/extract_load.py` | Loads CSVs into bronze: schema checks, idempotent loads, audit columns, transactions |
| `pipeline/config.py` | Settings from environment variables (no hard-coded paths) |
| `tests/` | Python unit tests (pytest) |
| `dbt_project/models/staging/` | Silver layer: typing, deduplication, latest version of each customer |
| `dbt_project/models/marts/` | Gold layer: dimension, incremental fact table, summary mart |
| `dbt_project/tests/` | Custom data tests (generic + singular) |
| `.github/workflows/` | CI and CD pipelines |
| `.sqlfluff` | SQL style rules |
| `pytest.ini` | Test settings |
| `scripts/generate_sample_data.py` | Re-creates the fictional sample data |
