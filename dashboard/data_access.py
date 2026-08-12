"""Read analytical outputs for the monitoring dashboard.

Loads DuckDB marts and anomaly tables. Does not recalculate KPI definitions.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

import config
from kpi.repository import (
    MART_CUSTOMER_SPEND,
    MART_DECLINE_RATES,
    MART_SPEND_KPIS,
    connect,
    require_marts,
)


def load_overview(duckdb_path: Path | None = None) -> dict:
    """Executive metrics from marts + anomaly tables."""
    con = connect(duckdb_path)
    try:
        require_marts(con)
        customers = con.execute(
            f"select count(*) from {MART_CUSTOMER_SPEND}"
        ).fetchone()[0]
        customers_with_tx = con.execute(
            f"select count(*) from {MART_CUSTOMER_SPEND} where transaction_count > 0"
        ).fetchone()[0]
        tx_volume = con.execute(
            "select count(*) from staging.stg_transactions"
        ).fetchone()[0]
        approved_spend = con.execute(
            f"select coalesce(sum(total_approved_spend), 0) from {MART_CUSTOMER_SPEND}"
        ).fetchone()[0]
        declined = con.execute(
            f"select coalesce(sum(declined_count), 0) from {MART_CUSTOMER_SPEND}"
        ).fetchone()[0]
        tx_total = con.execute(
            f"select coalesce(sum(transaction_count), 0) from {MART_CUSTOMER_SPEND}"
        ).fetchone()[0]
        decline_rate = (declined / tx_total) if tx_total else 0.0

        anomaly_count = 0
        high_severity_count = 0
        if _table_exists(con, "main", "anomaly_alerts"):
            anomaly_count = con.execute(
                "select count(*) from anomaly_alerts"
            ).fetchone()[0]
            high_severity_count = con.execute(
                "select count(*) from anomaly_alerts where severity = 'HIGH'"
            ).fetchone()[0]

        as_of = con.execute(
            f"select max(as_of_date) from {MART_SPEND_KPIS}"
        ).fetchone()[0]

        return {
            "as_of_date": as_of,
            "customers_monitored": int(customers),
            "customers_with_transactions": int(customers_with_tx),
            "transaction_volume": int(tx_volume),
            "total_approved_spend": float(approved_spend),
            "decline_rate": float(decline_rate),
            "anomaly_count": int(anomaly_count),
            "high_severity_anomaly_count": int(high_severity_count),
        }
    finally:
        con.close()


def load_spend_kpis(duckdb_path: Path | None = None) -> pd.DataFrame:
    con = connect(duckdb_path)
    try:
        require_marts(con)
        return con.execute(f"select * from {MART_SPEND_KPIS}").fetchdf()
    finally:
        con.close()


def load_customer_spend(duckdb_path: Path | None = None) -> pd.DataFrame:
    con = connect(duckdb_path)
    try:
        require_marts(con)
        return con.execute(f"select * from {MART_CUSTOMER_SPEND}").fetchdf()
    finally:
        con.close()


def load_decline_rates(duckdb_path: Path | None = None) -> pd.DataFrame:
    con = connect(duckdb_path)
    try:
        require_marts(con)
        return con.execute(f"select * from {MART_DECLINE_RATES}").fetchdf()
    finally:
        con.close()


def load_anomalies(duckdb_path: Path | None = None) -> pd.DataFrame:
    """Prefer narrated alerts; fall back to anomaly_alerts or CSV."""
    path = duckdb_path or config.DUCKDB_PATH
    if Path(path).is_file():
        con = duckdb.connect(str(path), read_only=True)
        try:
            if _table_exists(con, "main", "anomaly_alert_narrations"):
                return con.execute(
                    "select * from anomaly_alert_narrations"
                ).fetchdf()
            if _table_exists(con, "main", "anomaly_alerts"):
                df = con.execute("select * from anomaly_alerts").fetchdf()
                df["narration"] = None
                df["narration_source"] = None
                return df
        finally:
            con.close()

    if config.ANOMALIES_NARRATED_CSV.is_file():
        return pd.read_csv(config.ANOMALIES_NARRATED_CSV)
    if config.ANOMALIES_CSV.is_file():
        df = pd.read_csv(config.ANOMALIES_CSV)
        df["narration"] = None
        df["narration_source"] = None
        return df
    return pd.DataFrame()


def filter_anomalies(
    anomalies: pd.DataFrame,
    *,
    severities: list[str] | None = None,
    anomaly_types: list[str] | None = None,
    customer_id: str | None = None,
) -> pd.DataFrame:
    if anomalies.empty:
        return anomalies.copy()

    out = anomalies
    if severities:
        out = out[out["severity"].isin(severities)]
    if anomaly_types:
        out = out[out["anomaly_type"].isin(anomaly_types)]
    if customer_id and customer_id != "All":
        out = out[out["customer_id"] == customer_id]
    return out.reset_index(drop=True)


def load_customer_transactions(
    customer_id: str,
    duckdb_path: Path | None = None,
) -> pd.DataFrame:
    con = connect(duckdb_path)
    try:
        if not _table_exists(con, "staging", "stg_transactions"):
            return pd.DataFrame()
        return con.execute(
            """
            select
                transaction_id,
                transaction_timestamp,
                transaction_date,
                merchant_category,
                transaction_amount,
                transaction_status,
                card_type
            from staging.stg_transactions
            where customer_id = ?
            order by transaction_timestamp
            """,
            [customer_id],
        ).fetchdf()
    finally:
        con.close()


def weekly_decline_trend(duckdb_path: Path | None = None) -> pd.DataFrame:
    """Portfolio weekly decline rate from mart_decline_rates (no redefinition)."""
    declines = load_decline_rates(duckdb_path)
    if declines.empty:
        return declines
    grouped = (
        declines.groupby("period_start", as_index=False)
        .agg(
            transaction_count=("transaction_count", "sum"),
            declined_count=("declined_count", "sum"),
        )
        .sort_values("period_start")
    )
    grouped["decline_rate"] = grouped["declined_count"] / grouped[
        "transaction_count"
    ].replace(0, pd.NA)
    return grouped


def _table_exists(
    con: duckdb.DuckDBPyConnection, schema: str, table: str
) -> bool:
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
