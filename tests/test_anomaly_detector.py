"""Tests for rule-based anomaly detection."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import config
from anomaly.detector import (
    build_anomaly_frame,
    detect_anomalies,
    detect_category_shift,
    detect_decline_rate,
    detect_large_transactions,
    detect_spend_velocity,
    persist_anomalies,
)
from kpi.thresholds import MonitoringThresholds


def _kpi_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "as_of_date": "2025-12-31",
                "customer_id": "C0001",
                "card_type": "Gold",
                "spend_7d": 400.0,
                "spend_30d": 400.0,
                "spend_velocity": 4.0,
                "category_shift_score": 0.5,
                "category_shift_driver": "Travel",
                "txn_count_7d": 5,
                "txn_count_30d": 20,
                "declined_count_7d": 2,
                "declined_count_30d": 3,
                "decline_rate_7d": 0.4,
                "decline_rate_30d": 0.15,
            },
            {
                "as_of_date": "2025-12-31",
                "customer_id": "C0002",
                "card_type": "Classic",
                "spend_7d": 50.0,
                "spend_30d": 500.0,
                "spend_velocity": 0.4,
                "category_shift_score": 0.1,
                "category_shift_driver": "Dining",
                "txn_count_7d": 4,
                "txn_count_30d": 25,
                "declined_count_7d": 0,
                "declined_count_30d": 1,
                "decline_rate_7d": 0.0,
                "decline_rate_30d": 0.04,
            },
            {
                "as_of_date": "2025-12-31",
                "customer_id": "C0003",
                "card_type": "Platinum",
                "spend_7d": 900.0,
                "spend_30d": 900.0,
                "spend_velocity": 4.0,
                "category_shift_score": 0.8,
                "category_shift_driver": "Electronics",
                "txn_count_7d": 1,
                "txn_count_30d": 10,
                "declined_count_7d": 1,
                "declined_count_30d": 1,
                "decline_rate_7d": 1.0,
                "decline_rate_30d": 0.1,
            },
        ]
    )


def test_velocity_and_decline_detection_respects_activity_floor():
    thresholds = MonitoringThresholds(
        spend_velocity_min=2.0,
        category_shift_min=0.35,
        decline_rate_7d_min=0.15,
        min_txn_count_7d=3,
    )
    kpis = _kpi_rows()
    detected_at = "2026-01-01 00:00:00 UTC"

    velocity = detect_spend_velocity(kpis, thresholds, detected_at)
    decline = detect_decline_rate(kpis, thresholds, detected_at)
    shift = detect_category_shift(kpis, thresholds, detected_at)

    # C0001 flagged; C0002 normal; C0003 suppressed by activity floor
    assert [r["customer_id"] for r in velocity] == ["C0001"]
    assert [r["customer_id"] for r in decline] == ["C0001"]
    assert [r["customer_id"] for r in shift] == ["C0001"]
    assert all("spend_7d" in r["explanation_context"] for r in velocity)


def test_large_transaction_detection():
    customers = pd.DataFrame(
        [
            {
                "customer_id": "C0001",
                "card_type": "Gold",
                "max_approved_amount": 2_000.0,
                "total_approved_spend": 5_000.0,
                "top_category": "Travel",
            },
            {
                "customer_id": "C0002",
                "card_type": "Classic",
                "max_approved_amount": 200.0,
                "total_approved_spend": 800.0,
                "top_category": "Groceries",
            },
        ]
    )
    rows = detect_large_transactions(
        customers,
        MonitoringThresholds(large_transaction_amount_min=1_500.0),
        "2026-01-01 00:00:00 UTC",
        "2025-12-31",
    )
    assert len(rows) == 1
    assert rows[0]["customer_id"] == "C0001"
    assert rows[0]["metric_value"] == 2_000.0
    assert rows[0]["threshold_value"] == 1_500.0


def test_build_anomaly_frame_assigns_ids_severity_and_evidence():
    records = detect_spend_velocity(
        _kpi_rows(),
        MonitoringThresholds(spend_velocity_min=2.0, min_txn_count_7d=3),
        "2026-01-01 00:00:00 UTC",
    )
    records.extend(
        detect_category_shift(
            _kpi_rows(),
            MonitoringThresholds(category_shift_min=0.35, min_txn_count_7d=3),
            "2026-01-01 00:00:00 UTC",
        )
    )
    frame = build_anomaly_frame(records)
    assert list(frame.columns)[:8] == [
        "anomaly_id",
        "customer_id",
        "anomaly_type",
        "severity",
        "detected_timestamp",
        "metric_value",
        "threshold_value",
        "explanation_context",
    ]
    assert frame.iloc[0]["anomaly_id"] == "A000001"
    assert frame["severity"].isin(["LOW", "MEDIUM", "HIGH"]).all()
    c1 = frame[frame["customer_id"] == "C0001"]
    assert len(c1) == 2
    # velocity 4/2 → HIGH; shift 0.5/0.35 ≈ 1.43 → LOW then bumped to MEDIUM (2 signals)
    assert set(c1["severity"]) == {"HIGH", "MEDIUM"}
    assert (frame["metric_value"] >= frame["threshold_value"]).all()


@pytest.mark.skipif(
    not config.DUCKDB_PATH.is_file(),
    reason="DuckDB warehouse not built",
)
def test_detect_anomalies_integration(tmp_path: Path):
    try:
        anomalies = detect_anomalies(detected_at="2026-01-01 00:00:00 UTC")
    except RuntimeError:
        pytest.skip("dbt marts not built")

    assert set(anomalies["anomaly_type"]).issubset(
        {"spend_velocity", "category_shift", "decline_rate", "large_transaction"}
    )
    assert anomalies["anomaly_id"].is_unique
    assert anomalies["severity"].isin(["LOW", "MEDIUM", "HIGH"]).all()
    assert anomalies["metric_value"].notna().all()
    assert anomalies["threshold_value"].notna().all()

    out = tmp_path / "anomalies.csv"
    persist_anomalies(anomalies, csv_path=out, duckdb_path=config.DUCKDB_PATH)
    assert out.is_file()
    reloaded = pd.read_csv(out)
    assert len(reloaded) == len(anomalies)
