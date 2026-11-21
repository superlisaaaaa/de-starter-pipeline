"""Extract raw CSV files from the landing zone and load them into DuckDB (bronze).

Data-engineering principles shown in this file
-----------------------------------------------
1. Fail fast on schema changes  -> validate_columns()
2. Keep raw data raw             -> every value is stored as text, exactly as received
3. Idempotent loads              -> a hash of each row is the primary key, so loading
                                    the same file twice never creates duplicates
4. Audit columns                 -> _batch_id, _source_file, _loaded_at on every row
5. Observability                 -> a load log table records what was loaded and when

Run it:
    python -m pipeline.extract_load
"""

from __future__ import annotations

import csv
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from pipeline import config

log = logging.getLogger(__name__)


class SchemaError(Exception):
    """Raised when a source file does not have the columns we expect."""


# ---------------------------------------------------------------------------
# Small, pure functions: easy to unit test (see tests/test_extract_load.py)
# ---------------------------------------------------------------------------

def compute_row_hash(values: list[str]) -> str:
    """Return a stable fingerprint for one row.

    The same values always give the same hash, so we can use it to detect
    rows we have already loaded. The separator avoids collisions such as
    ["ab", "c"] vs ["a", "bc"].
    """
    joined = `""`.join("" if v is None else str(v) for v in values)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()


def validate_columns(table: str, actual: list[str], expected: list[str]) -> None:
    """Fail loudly if the file is missing columns or has unexpected ones."""
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    if missing or extra:
        raise SchemaError(
            f"{table}: schema mismatch. missing={missing} unexpected={extra}"
        )


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Read a CSV file and return (header, rows). Values stay as text."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [row for row in reader if row]
    return header, rows


# ---------------------------------------------------------------------------
# Database work
# ---------------------------------------------------------------------------

def ensure_bronze_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create the bronze schema, tables and load log if they don't exist yet."""
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {config.BRONZE_SCHEMA}")
    for table, columns in config.EXPECTED_TABLES.items():
        cols_sql = ",\n    ".join(f"{c} VARCHAR" for c in columns)
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {config.BRONZE_SCHEMA}.{table} (
                {cols_sql},
                _row_hash    VARCHAR PRIMARY KEY,
                _batch_id    VARCHAR NOT NULL,
                _source_file VARCHAR NOT NULL,
                _loaded_at   TIMESTAMP NOT NULL
            )
        """)
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {config.BRONZE_SCHEMA}._load_log (
            batch_id      VARCHAR,
            table_name    VARCHAR,
            rows_in_file  INTEGER,
            rows_inserted INTEGER,
            loaded_at     TIMESTAMP
        )
    """)


def load_file(con: duckdb.DuckDBPyConnection, table: str, path: Path, batch_id: str) -> int:
    """Load one CSV file into its bronze table. Returns the number of NEW rows."""
    expected = config.EXPECTED_TABLES[table]
    header, rows = read_csv(path)
    validate_columns(table, header, expected)

    # Re-order every row into the expected column order
    idx = [header.index(c) for c in expected]
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    records = []
    for row in rows:
        values = [row[i] if row[i] != "" else None for i in idx]
        records.append(values + [compute_row_hash(values), batch_id, path.name, loaded_at])

    full_table = f"{config.BRONZE_SCHEMA}.{table}"
    before = con.execute(f"SELECT count(*) FROM {full_table}").fetchone()[0]
    if records:
        placeholders = ", ".join(["?"] * (len(expected) + 4))
        # ON CONFLICT DO NOTHING = idempotency: rows we already have are skipped
        con.executemany(
            f"INSERT INTO {full_table} VALUES ({placeholders}) ON CONFLICT DO NOTHING",
            records,
        )
    after = con.execute(f"SELECT count(*) FROM {full_table}").fetchone()[0]
    inserted = after - before

    con.execute(
        f"INSERT INTO {config.BRONZE_SCHEMA}._load_log VALUES (?, ?, ?, ?, ?)",
        [batch_id, table, len(rows), inserted, loaded_at],
    )
    log.info("%-15s batch=%s rows_in_file=%3d new_rows=%3d", table, batch_id, len(rows), inserted)
    return inserted


def load_batch(con: duckdb.DuckDBPyConnection, batch_dir: Path) -> dict[str, int]:
    """Load every expected file in one batch folder (e.g. data/landing/2026-10-01)."""
    batch_id = batch_dir.name
    results = {}
    for table in config.EXPECTED_TABLES:
        path = batch_dir / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Batch {batch_id} is missing {path.name}")
        results[table] = load_file(con, table, path, batch_id)
    return results


def run(landing_dir: Path = config.LANDING_DIR, db_path: Path = config.DUCKDB_PATH) -> None:
    """Load all batches in date order. Safe to run again and again."""
    batches = sorted(p for p in landing_dir.iterdir() if p.is_dir())
    if not batches:
        raise FileNotFoundError(f"No batch folders found in {landing_dir}")

    con = duckdb.connect(str(db_path))
    try:
        ensure_bronze_tables(con)
        for batch_dir in batches:
            # One transaction per batch: either the whole batch loads, or nothing does
            con.execute("BEGIN TRANSACTION")
            try:
                load_batch(con, batch_dir)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
    finally:
        con.close()
    log.info("Done. Warehouse: %s", db_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
