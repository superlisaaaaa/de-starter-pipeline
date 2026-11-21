"""Unit tests for the extract/load step.

Run them with:
    pytest -v

Each test uses a temporary folder and a temporary database (tmp_path),
so tests never touch your real warehouse.duckdb.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from pipeline import config
from pipeline.extract_load import (
    SchemaError,
    compute_row_hash,
    ensure_bronze_tables,
    load_file,
    run,
    validate_columns,
)


# ---------- helpers ----------

def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_batch(root: Path, name: str, readings: str) -> Path:
    batch = root / name
    write(batch / "customers.csv",
          "customer_id,first_name,email,country,signup_channel,updated_at\n"
          "C001,Alva,alva@example.com,SE,digital,2026-10-01T06:00:00\n")
    write(batch / "contracts.csv",
          "contract_id,customer_id,product,start_date,end_date\n"
          "K001,C001,spot,2026-01-01,\n")
    write(batch / "meter_readings.csv", "contract_id,reading_date,kwh\n" + readings)
    return batch


# ---------- pure functions ----------

def test_row_hash_is_stable():
    assert compute_row_hash(["a", "b"]) == compute_row_hash(["a", "b"])


def test_row_hash_differs_when_values_differ():
    assert compute_row_hash(["a", "b"]) != compute_row_hash(["a", "c"])


def test_row_hash_avoids_concatenation_collisions():
    assert compute_row_hash(["ab", "c"]) != compute_row_hash(["a", "bc"])


def test_validate_columns_passes_for_expected_schema():
    validate_columns("t", ["a", "b"], ["a", "b"])  # no error = pass


def test_validate_columns_fails_on_missing_column():
    with pytest.raises(SchemaError, match="missing"):
        validate_columns("t", ["a"], ["a", "b"])


# ---------- database behaviour ----------

def test_loading_same_file_twice_is_idempotent(tmp_path):
    con = duckdb.connect(str(tmp_path / "test.duckdb"))
    ensure_bronze_tables(con)
    f = write(tmp_path / "meter_readings.csv",
              "contract_id,reading_date,kwh\nK001,2026-10-01,10.5\nK001,2026-10-02,11.0\n")

    first = load_file(con, "meter_readings", f, "batch-1")
    second = load_file(con, "meter_readings", f, "batch-1")

    total = con.execute(f"SELECT count(*) FROM {config.BRONZE_SCHEMA}.meter_readings").fetchone()[0]
    assert (first, second, total) == (2, 0, 2)


def test_full_run_twice_gives_same_row_counts(tmp_path):
    landing = tmp_path / "landing"
    make_batch(landing, "2026-10-01", "K001,2026-10-01,10.5\n")
    make_batch(landing, "2026-10-02", "K001,2026-10-01,10.5\nK001,2026-10-02,9.0\n")
    db = tmp_path / "wh.duckdb"

    run(landing, db)
    run(landing, db)  # second run must not add anything

    con = duckdb.connect(str(db))
    n = con.execute(f"SELECT count(*) FROM {config.BRONZE_SCHEMA}.meter_readings").fetchone()[0]
    assert n == 2  # the duplicate row across batches is stored once


def test_bad_batch_is_rolled_back(tmp_path):
    landing = tmp_path / "landing"
    batch = make_batch(landing, "2026-10-01", "K001,2026-10-01,10.5\n")
    # break the schema of one file in the batch
    write(batch / "meter_readings.csv", "contract_id,day,kwh\nK001,2026-10-01,10.5\n")
    db = tmp_path / "wh.duckdb"

    with pytest.raises(SchemaError):
        run(landing, db)

    con = duckdb.connect(str(db))
    n = con.execute(f"SELECT count(*) FROM {config.BRONZE_SCHEMA}.customers").fetchone()[0]
    assert n == 0  # customers loaded before the error were rolled back too
