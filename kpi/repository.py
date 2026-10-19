"""Read dbt mart outputs from DuckDB. Does not recalculate KPIs."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

import config

MART_SPEND_KPIS = "marts.mart_spend_kpis"
MART_CUSTOMER_SPEND = "marts.mart_customer_spend"
MART_DECLINE_RATES = "marts.mart_decline_rates"


def connect(duckdb_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = duckdb_path or config.DUCKDB_PATH
    if not Path(path).is_file():
        raise FileNotFoundError(
            f"DuckDB warehouse not found: {path}. Run: make ingest && make dbt-run"
        )
    return duckdb.connect(str(path), read_only=True)


def _table_exists(con: duckdb.DuckDBPyConnection, qualified_name: str) -> bool:
    schema, table = qualified_name.split(".", 1)
    row = con.execute(
        """
        select 1
        from information_schema.tables
        where table_schema = ? and table_name = ?
        limit 1
        """,
        [schema, table],
    ).fetchone()
    return row is not None


def require_marts(con: duckdb.DuckDBPyConnection) -> None:
    missing = [
        name
        for name in (MART_SPEND_KPIS, MART_CUSTOMER_SPEND, MART_DECLINE_RATES)
        if not _table_exists(con, name)
    ]
    if missing:
        raise RuntimeError(
            "Missing dbt marts: "
            + ", ".join(missing)
            + ". Run: make dbt-run"
        )


def load_spend_kpis(
    duckdb_path: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> pd.DataFrame:
    owns_connection = con is None
    con = con or connect(duckdb_path)
    try:
        require_marts(con)
        return con.execute(f"select * from {MART_SPEND_KPIS}").fetchdf()
    finally:
        if owns_connection:
            con.close()


def load_customer_spend(
    duckdb_path: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> pd.DataFrame:
    owns_connection = con is None
    con = con or connect(duckdb_path)
    try:
        require_marts(con)
        return con.execute(f"select * from {MART_CUSTOMER_SPEND}").fetchdf()
    finally:
        if owns_connection:
            con.close()


def load_decline_rates(
    duckdb_path: Path | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> pd.DataFrame:
    owns_connection = con is None
    con = con or connect(duckdb_path)
    try:
        require_marts(con)
        return con.execute(f"select * from {MART_DECLINE_RATES}").fetchdf()
    finally:
        if owns_connection:
            con.close()
