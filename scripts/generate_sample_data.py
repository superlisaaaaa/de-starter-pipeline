"""Generate fictional sample data for the "Nordlys Energy" learning project.

All customers, contracts and readings are made up. The script is deterministic
(fixed random seed), so everyone who runs it gets exactly the same files.

It writes two daily "batches" into data/landing/, the way a source system
might drop new files every day:

    data/landing/2026-10-01/customers.csv
    data/landing/2026-10-01/contracts.csv
    data/landing/2026-10-01/meter_readings.csv
    data/landing/2026-10-02/...

Batch 2 deliberately contains some messy data so you can practise
data-quality checks:
  * one meter reading that is an exact duplicate of a batch-1 row
    (the loader's row hash stores it only once)
  * one customer who changed email (a newer version of the same customer)
  * one meter reading with a negative kWh value

Usage:
    python scripts/generate_sample_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "data" / "landing"

COUNTRIES = ["SE", "NO", "FI"]
CHANNELS = ["digital", "phone", "partner"]
PRODUCTS = ["fixed_12m", "variable", "spot"]
FIRST_NAMES = ["Alva", "Noah", "Ella", "Liam", "Saga", "Oskar", "Maja", "Elias",
               "Freja", "Hugo", "Ingrid", "Emil", "Sofia", "Lukas", "Nora"]


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"wrote {len(rows):>4} rows -> {path.relative_to(ROOT)}")


def main() -> None:
    rng = random.Random(42)

    # ---------- customers ----------
    customers = []
    for i in range(1, 16):
        name = FIRST_NAMES[i - 1]
        customers.append([
            f"C{i:03d}",
            name,
            f"{name.lower()}@example.com",
            rng.choice(COUNTRIES),
            rng.choice(CHANNELS),
            "2026-10-01T06:00:00",  # updated_at
        ])

    # ---------- contracts ----------
    contracts = []
    for i, cust in enumerate(customers, start=1):
        start = date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))
        contracts.append([
            f"K{i:03d}",
            cust[0],
            rng.choice(PRODUCTS),
            start.isoformat(),
            "",  # end_date empty = still active
        ])
    # one customer has churned
    contracts[3][4] = "2026-09-15"

    # ---------- meter readings: batch 1 = 2026-09-24..2026-09-30 ----------
    def readings_for(days: list[date]) -> list[list]:
        rows = []
        for k in contracts:
            for d in days:
                kwh = round(rng.uniform(4, 40), 2)
                rows.append([k[0], d.isoformat(), kwh])
        return rows

    batch1_days = [date(2026, 9, 24) + timedelta(days=n) for n in range(7)]
    batch2_days = [date(2026, 10, 1)]
    readings_b1 = readings_for(batch1_days)
    readings_b2 = readings_for(batch2_days)

    # messy data in batch 2
    readings_b2.append(list(readings_b1[0]))            # exact duplicate of a batch-1 row
    for row in readings_b2:                             # negative value (meter error)
        if row[0] == "K005":
            row[2] = -12.5

    customers_b2 = [list(customers[1])]                 # customer C002 changed email
    customers_b2[0][2] = "noah.new@example.com"
    customers_b2[0][5] = "2026-10-02T06:00:00"

    cust_header = ["customer_id", "first_name", "email", "country", "signup_channel", "updated_at"]
    contract_header = ["contract_id", "customer_id", "product", "start_date", "end_date"]
    reading_header = ["contract_id", "reading_date", "kwh"]

    b1 = LANDING / "2026-10-01"
    write_csv(b1 / "customers.csv", cust_header, customers)
    write_csv(b1 / "contracts.csv", contract_header, contracts)
    write_csv(b1 / "meter_readings.csv", reading_header, readings_b1)

    b2 = LANDING / "2026-10-02"
    write_csv(b2 / "customers.csv", cust_header, customers_b2)
    write_csv(b2 / "contracts.csv", contract_header, [])
    write_csv(b2 / "meter_readings.csv", reading_header, readings_b2)


if __name__ == "__main__":
    main()
