"""Central settings for the pipeline.

Principle: never hard-code paths or secrets inside the logic. Read them from
environment variables, with safe defaults for local development. In CI we can
then point the pipeline at a different database just by setting a variable.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Where the raw files arrive (the "landing zone")
LANDING_DIR = Path(os.getenv("LANDING_DIR", ROOT / "data" / "landing"))

# The local DuckDB file that acts as our data warehouse
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", ROOT / "warehouse.duckdb"))

# Schema for raw data loaded as-is (the "bronze" layer)
BRONZE_SCHEMA = "bronze"

# The tables we expect in every batch, and the columns each must have.
# If a source system suddenly drops or renames a column, we want the load
# to fail loudly instead of silently loading broken data.
EXPECTED_TABLES: dict[str, list[str]] = {
    "customers": ["customer_id", "first_name", "email", "country", "signup_channel", "updated_at"],
    "contracts": ["contract_id", "customer_id", "product", "start_date", "end_date"],
    "meter_readings": ["contract_id", "reading_date", "kwh"],
}
