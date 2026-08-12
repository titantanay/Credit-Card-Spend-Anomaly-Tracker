"""Tests for dashboard data access (no Streamlit runtime required)."""

from __future__ import annotations

import pandas as pd
import pytest

import config
from dashboard.data_access import filter_anomalies, load_anomalies, load_overview
from dashboard.components.formatting import format_currency, format_pct


def test_formatters():
    assert format_currency(7975800.5) == "$7,975,800"
    assert format_currency(7975800.500000004) == "$7,975,800"
    assert format_pct(0.0609) == "6.09%"


def test_filter_anomalies_by_severity_and_type():
    frame = pd.DataFrame(
        [
            {
                "customer_id": "C1",
                "severity": "HIGH",
                "anomaly_type": "spend_velocity",
            },
            {
                "customer_id": "C2",
                "severity": "LOW",
                "anomaly_type": "decline_rate",
            },
            {
                "customer_id": "C1",
                "severity": "MEDIUM",
                "anomaly_type": "category_shift",
            },
        ]
    )
    filtered = filter_anomalies(
        frame, severities=["HIGH"], anomaly_types=["spend_velocity"]
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["customer_id"] == "C1"

    empty = filter_anomalies(frame, severities=["HIGH"], anomaly_types=["decline_rate"])
    assert empty.empty

    by_customer = filter_anomalies(frame, customer_id="C1")
    assert len(by_customer) == 2


def test_filter_empty_frame():
    out = filter_anomalies(pd.DataFrame(), severities=["HIGH"])
    assert out.empty


@pytest.mark.skipif(not config.DUCKDB_PATH.is_file(), reason="warehouse missing")
def test_overview_reconciles_with_duckdb():
    overview = load_overview()
    assert overview["transaction_volume"] == 50_000
    assert overview["customers_monitored"] == 1_000
    assert abs(overview["total_approved_spend"] - 7_975_800.5) < 0.01
    assert abs(overview["decline_rate"] - 0.06086) < 1e-4
    assert overview["anomaly_count"] >= 0
    assert overview["high_severity_anomaly_count"] <= overview["anomaly_count"]


@pytest.mark.skipif(not config.DUCKDB_PATH.is_file(), reason="warehouse missing")
def test_load_anomalies_includes_narration_when_present():
    anomalies = load_anomalies()
    if anomalies.empty:
        pytest.skip("no anomaly tables")
    assert "severity" in anomalies.columns
    assert "metric_value" in anomalies.columns
    assert "threshold_value" in anomalies.columns
    # Narration columns present (may be fallback text)
    assert "narration" in anomalies.columns
    assert anomalies["narration"].notna().all()
    if "narration_source" in anomalies.columns:
        assert set(anomalies["narration_source"].dropna().unique()).issubset(
            {"ollama", "fallback"}
        )


@pytest.mark.skipif(not config.DUCKDB_PATH.is_file(), reason="warehouse missing")
def test_customer_filter_selects_single_customer():
    anomalies = load_anomalies()
    if anomalies.empty:
        pytest.skip("no anomaly tables")
    customer = anomalies["customer_id"].iloc[0]
    filtered = filter_anomalies(anomalies, customer_id=customer)
    assert not filtered.empty
    assert (filtered["customer_id"] == customer).all()


def test_missing_narration_columns_tolerated_by_filter():
    """Filter works on bare alert frames without narration."""
    frame = pd.DataFrame(
        [
            {
                "customer_id": "C9",
                "severity": "HIGH",
                "anomaly_type": "large_transaction",
            }
        ]
    )
    out = filter_anomalies(frame, severities=["HIGH"])
    assert len(out) == 1
    assert "narration" not in out.columns
