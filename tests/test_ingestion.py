"""Tests for DuckDB raw ingestion."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from data_generator.generate_transactions import (
    CUSTOMER_COLUMNS,
    TRANSACTION_COLUMNS,
)
from ingestion.load_to_duckdb import (
    RAW_CUSTOMERS_TABLE,
    RAW_TRANSACTIONS_TABLE,
    ingest,
    read_transactions_csv,
    validate_columns,
)


def _sample_customers() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "customer_id": "C0001",
                "customer_name": "Alex Nguyen",
                "card_type": "Gold",
                "credit_limit": 8000,
                "customer_since": "2020-01-15",
            },
            {
                "customer_id": "C0002",
                "customer_name": "Jordan Patel",
                "card_type": "Classic",
                "credit_limit": 3000,
                "customer_since": "2021-06-01",
            },
        ],
        columns=CUSTOMER_COLUMNS,
    )


def _sample_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "T00000001",
                "customer_id": "C0001",
                "transaction_timestamp": "2025-11-01 10:00:00",
                "merchant_category": "Dining",
                "transaction_amount": 42.5,
                "transaction_status": "approved",
                "card_type": "Gold",
            },
            {
                "transaction_id": "T00000002",
                "customer_id": "C0002",
                "transaction_timestamp": "2025-11-02 14:30:00",
                "merchant_category": "Travel",
                "transaction_amount": 500.0,
                "transaction_status": "declined",
                "card_type": "Classic",
            },
            {
                "transaction_id": "T00000003",
                "customer_id": "C0001",
                "transaction_timestamp": "2025-11-03 09:15:00",
                "merchant_category": "Groceries",
                "transaction_amount": 88.2,
                "transaction_status": "approved",
                "card_type": "Gold",
            },
        ],
        columns=TRANSACTION_COLUMNS,
    )


def test_validate_columns_rejects_missing():
    df = pd.DataFrame({"transaction_id": ["T1"]})
    with pytest.raises(ValueError, match="missing"):
        validate_columns(df, TRANSACTION_COLUMNS, "transactions")


def test_read_transactions_csv_validates(tmp_path: Path):
    path = tmp_path / "transactions.csv"
    _sample_transactions().to_csv(path, index=False)
    df = read_transactions_csv(path)
    assert list(df.columns) == TRANSACTION_COLUMNS
    assert len(df) == 3


def test_ingest_creates_raw_tables(tmp_path: Path):
    tx_path = tmp_path / "transactions.csv"
    cust_path = tmp_path / "customers.csv"
    db_path = tmp_path / "test.duckdb"
    _sample_transactions().to_csv(tx_path, index=False)
    _sample_customers().to_csv(cust_path, index=False)

    counts = ingest(
        duckdb_path=db_path,
        transactions_csv=tx_path,
        customers_csv=cust_path,
    )

    assert counts[RAW_TRANSACTIONS_TABLE] == 3
    assert counts[RAW_CUSTOMERS_TABLE] == 2

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        tx_cols = [
            r[0]
            for r in con.execute(
                f"DESCRIBE {RAW_TRANSACTIONS_TABLE}"
            ).fetchall()
        ]
        assert tx_cols == TRANSACTION_COLUMNS
        n = con.execute(
            f"SELECT COUNT(*) FROM {RAW_TRANSACTIONS_TABLE}"
        ).fetchone()[0]
        assert n == 3
    finally:
        con.close()


def test_ingest_is_idempotent(tmp_path: Path):
    tx_path = tmp_path / "transactions.csv"
    cust_path = tmp_path / "customers.csv"
    db_path = tmp_path / "test.duckdb"
    _sample_transactions().to_csv(tx_path, index=False)
    _sample_customers().to_csv(cust_path, index=False)

    ingest(duckdb_path=db_path, transactions_csv=tx_path, customers_csv=cust_path)
    counts = ingest(
        duckdb_path=db_path, transactions_csv=tx_path, customers_csv=cust_path
    )
    assert counts[RAW_TRANSACTIONS_TABLE] == 3
