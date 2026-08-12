"""Load raw CSVs into the local DuckDB warehouse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

import config
from data_generator.generate_transactions import (
    CUSTOMER_COLUMNS,
    TRANSACTION_COLUMNS,
)

RAW_TRANSACTIONS_TABLE = "raw_transactions"
RAW_CUSTOMERS_TABLE = "raw_customers"


def validate_columns(df: pd.DataFrame, expected: list[str], label: str) -> None:
    missing = [c for c in expected if c not in df.columns]
    unexpected = [c for c in df.columns if c not in expected]
    if missing or unexpected:
        parts = []
        if missing:
            parts.append(f"missing={missing}")
        if unexpected:
            parts.append(f"unexpected={unexpected}")
        raise ValueError(f"{label} schema mismatch: {', '.join(parts)}")


def read_transactions_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Transactions CSV not found: {path}. Run: make generate-data"
        )
    df = pd.read_csv(path)
    validate_columns(df, TRANSACTION_COLUMNS, "transactions")
    return df


def read_customers_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Customers CSV not found: {path}. Run: make generate-data"
        )
    df = pd.read_csv(path)
    validate_columns(df, CUSTOMER_COLUMNS, "customers")
    return df


def load_frames(
    con: duckdb.DuckDBPyConnection,
    transactions: pd.DataFrame,
    customers: pd.DataFrame,
) -> dict[str, int]:
    con.execute(f"DROP TABLE IF EXISTS {RAW_TRANSACTIONS_TABLE}")
    con.execute(f"DROP TABLE IF EXISTS {RAW_CUSTOMERS_TABLE}")
    con.register("_tx_df", transactions)
    con.register("_cust_df", customers)
    con.execute(
        f"CREATE TABLE {RAW_TRANSACTIONS_TABLE} AS SELECT * FROM _tx_df"
    )
    con.execute(f"CREATE TABLE {RAW_CUSTOMERS_TABLE} AS SELECT * FROM _cust_df")
    con.unregister("_tx_df")
    con.unregister("_cust_df")

    tx_count = con.execute(
        f"SELECT COUNT(*) FROM {RAW_TRANSACTIONS_TABLE}"
    ).fetchone()[0]
    cust_count = con.execute(
        f"SELECT COUNT(*) FROM {RAW_CUSTOMERS_TABLE}"
    ).fetchone()[0]
    return {
        RAW_TRANSACTIONS_TABLE: int(tx_count),
        RAW_CUSTOMERS_TABLE: int(cust_count),
    }


def ingest(
    duckdb_path: Path | None = None,
    transactions_csv: Path | None = None,
    customers_csv: Path | None = None,
) -> dict[str, int]:
    duckdb_path = duckdb_path or config.DUCKDB_PATH
    transactions_csv = transactions_csv or config.RAW_TRANSACTIONS_CSV
    customers_csv = customers_csv or config.CUSTOMERS_CSV

    config.ensure_data_dirs()
    transactions = read_transactions_csv(transactions_csv)
    customers = read_customers_csv(customers_csv)

    con = duckdb.connect(str(duckdb_path))
    try:
        counts = load_frames(con, transactions, customers)
    finally:
        con.close()

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load synthetic CSVs into DuckDB raw tables."
    )
    parser.add_argument(
        "--duckdb-path",
        type=Path,
        default=None,
        help="Override DuckDB file path (default: config.DUCKDB_PATH)",
    )
    parser.add_argument(
        "--transactions-csv",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--customers-csv",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    try:
        counts = ingest(
            duckdb_path=args.duckdb_path,
            transactions_csv=args.transactions_csv,
            customers_csv=args.customers_csv,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        sys.exit(1)

    db_path = args.duckdb_path or config.DUCKDB_PATH
    print(f"DuckDB: {db_path}")
    for table, n in counts.items():
        print(f"  {table}: {n:,} rows")


if __name__ == "__main__":
    main()
