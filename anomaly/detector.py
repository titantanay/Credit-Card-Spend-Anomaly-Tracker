"""Rule-based anomaly detection over dbt KPI marts.

Deterministic analytics decide what is anomalous. Thresholds come from
kpi.thresholds. Severity is assigned in severity.py from breach magnitude
and multi-signal coincidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

import config
from anomaly.severity import apply_severity
from kpi.repository import connect, load_customer_spend, load_spend_kpis, require_marts
from kpi.thresholds import DEFAULT_THRESHOLDS, MonitoringThresholds

ANOMALY_COLUMNS = [
    "anomaly_id",
    "customer_id",
    "anomaly_type",
    "severity",
    "detected_timestamp",
    "metric_value",
    "threshold_value",
    "explanation_context",
    "as_of_date",
    "card_type",
]

ANOMALY_TYPES = (
    "spend_velocity",
    "category_shift",
    "decline_rate",
    "large_transaction",
)


def _context(**fields: object) -> str:
    return json.dumps(fields, default=str, sort_keys=True)


def _active_mask(kpis: pd.DataFrame, thresholds: MonitoringThresholds) -> pd.Series:
    return kpis["txn_count_7d"].fillna(0) >= thresholds.min_txn_count_7d


def detect_spend_velocity(
    kpis: pd.DataFrame,
    thresholds: MonitoringThresholds,
    detected_at: str,
) -> list[dict]:
    active = _active_mask(kpis, thresholds)
    flagged = kpis[
        active
        & kpis["spend_velocity"].notna()
        & (kpis["spend_velocity"] >= thresholds.spend_velocity_min)
    ]
    rows = []
    for _, row in flagged.iterrows():
        metric = float(row["spend_velocity"])
        threshold = float(thresholds.spend_velocity_min)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "anomaly_type": "spend_velocity",
                "detected_timestamp": detected_at,
                "metric_value": metric,
                "threshold_value": threshold,
                "as_of_date": row["as_of_date"],
                "card_type": row["card_type"],
                "explanation_context": _context(
                    rule="spend_7d / (spend_30d * 7/30) >= threshold",
                    spend_7d=row["spend_7d"],
                    spend_30d=row["spend_30d"],
                    txn_count_7d=int(row["txn_count_7d"]),
                ),
            }
        )
    return rows


def detect_category_shift(
    kpis: pd.DataFrame,
    thresholds: MonitoringThresholds,
    detected_at: str,
) -> list[dict]:
    active = _active_mask(kpis, thresholds)
    flagged = kpis[
        active & (kpis["category_shift_score"] >= thresholds.category_shift_min)
    ]
    rows = []
    for _, row in flagged.iterrows():
        metric = float(row["category_shift_score"])
        threshold = float(thresholds.category_shift_min)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "anomaly_type": "category_shift",
                "detected_timestamp": detected_at,
                "metric_value": metric,
                "threshold_value": threshold,
                "as_of_date": row["as_of_date"],
                "card_type": row["card_type"],
                "explanation_context": _context(
                    rule="max(|share_7d - share_baseline|) >= threshold",
                    category_shift_driver=row.get("category_shift_driver"),
                    txn_count_7d=int(row["txn_count_7d"]),
                ),
            }
        )
    return rows


def detect_decline_rate(
    kpis: pd.DataFrame,
    thresholds: MonitoringThresholds,
    detected_at: str,
) -> list[dict]:
    active = _active_mask(kpis, thresholds)
    flagged = kpis[
        active
        & kpis["decline_rate_7d"].notna()
        & (kpis["decline_rate_7d"] >= thresholds.decline_rate_7d_min)
    ]
    rows = []
    for _, row in flagged.iterrows():
        metric = float(row["decline_rate_7d"])
        threshold = float(thresholds.decline_rate_7d_min)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "anomaly_type": "decline_rate",
                "detected_timestamp": detected_at,
                "metric_value": metric,
                "threshold_value": threshold,
                "as_of_date": row["as_of_date"],
                "card_type": row["card_type"],
                "explanation_context": _context(
                    rule="declined_count_7d / txn_count_7d >= threshold",
                    declined_count_7d=int(row["declined_count_7d"]),
                    txn_count_7d=int(row["txn_count_7d"]),
                    decline_rate_30d=row.get("decline_rate_30d"),
                ),
            }
        )
    return rows


def detect_large_transactions(
    customers: pd.DataFrame,
    thresholds: MonitoringThresholds,
    detected_at: str,
    as_of_date: object,
) -> list[dict]:
    flagged = customers[
        customers["max_approved_amount"] >= thresholds.large_transaction_amount_min
    ]
    rows = []
    for _, row in flagged.iterrows():
        metric = float(row["max_approved_amount"])
        threshold = float(thresholds.large_transaction_amount_min)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "anomaly_type": "large_transaction",
                "detected_timestamp": detected_at,
                "metric_value": metric,
                "threshold_value": threshold,
                "as_of_date": as_of_date,
                "card_type": row["card_type"],
                "explanation_context": _context(
                    rule="max approved ticket >= threshold",
                    max_approved_amount=metric,
                    total_approved_spend=row.get("total_approved_spend"),
                    top_category=row.get("top_category"),
                ),
            }
        )
    return rows


def build_anomaly_frame(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=ANOMALY_COLUMNS)

    frame = pd.DataFrame(records)
    frame = apply_severity(frame)
    frame = frame.sort_values(
        ["customer_id", "anomaly_type", "metric_value"],
        ascending=[True, True, False],
    ).reset_index(drop=True)
    frame.insert(
        0,
        "anomaly_id",
        [f"A{i + 1:06d}" for i in range(len(frame))],
    )
    return frame[ANOMALY_COLUMNS]


def detect_anomalies(
    thresholds: MonitoringThresholds = DEFAULT_THRESHOLDS,
    duckdb_path: Path | None = None,
    detected_at: str | None = None,
) -> pd.DataFrame:
    detected_at = detected_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    con = connect(duckdb_path)
    try:
        require_marts(con)
        kpis = load_spend_kpis(con=con)
        customers = load_customer_spend(con=con)
    finally:
        con.close()

    as_of = kpis["as_of_date"].iloc[0] if len(kpis) else None
    records: list[dict] = []
    records.extend(detect_spend_velocity(kpis, thresholds, detected_at))
    records.extend(detect_category_shift(kpis, thresholds, detected_at))
    records.extend(detect_decline_rate(kpis, thresholds, detected_at))
    records.extend(
        detect_large_transactions(customers, thresholds, detected_at, as_of)
    )
    return build_anomaly_frame(records)


def persist_anomalies(
    anomalies: pd.DataFrame,
    csv_path: Path | None = None,
    duckdb_path: Path | None = None,
) -> tuple[Path, Path]:
    config.ensure_data_dirs()
    csv_path = csv_path or config.ANOMALIES_CSV
    duckdb_path = duckdb_path or config.DUCKDB_PATH

    anomalies.to_csv(csv_path, index=False)

    con = duckdb.connect(str(duckdb_path))
    try:
        con.register("_anomalies_df", anomalies)
        con.execute("create or replace table anomaly_alerts as select * from _anomalies_df")
        con.unregister("_anomalies_df")
    finally:
        con.close()

    return csv_path, duckdb_path


def run(
    thresholds: MonitoringThresholds = DEFAULT_THRESHOLDS,
    duckdb_path: Path | None = None,
    csv_path: Path | None = None,
) -> pd.DataFrame:
    anomalies = detect_anomalies(thresholds=thresholds, duckdb_path=duckdb_path)
    persist_anomalies(anomalies, csv_path=csv_path, duckdb_path=duckdb_path)
    return anomalies


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect spend anomalies from dbt KPI marts."
    )
    parser.add_argument(
        "--duckdb-path",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Anomalies CSV path (default: data/processed/anomalies.csv)",
    )
    args = parser.parse_args()

    anomalies = run(duckdb_path=args.duckdb_path, csv_path=args.output)
    csv_path = args.output or config.ANOMALIES_CSV

    print(f"Wrote {len(anomalies):,} anomaly alerts → {csv_path}")
    if len(anomalies):
        print(anomalies["anomaly_type"].value_counts().to_string())
        print("severity:")
        print(anomalies["severity"].value_counts().to_string())


if __name__ == "__main__":
    main()
