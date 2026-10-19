"""Tests for the KPI layer (mart access + threshold config)."""

from __future__ import annotations

import pandas as pd
import pytest

import config
from kpi.repository import connect, load_spend_kpis, require_marts
from kpi.summarize import summarize_spend_kpis
from kpi.thresholds import DEFAULT_THRESHOLDS, MonitoringThresholds


def test_default_thresholds_are_positive():
    t = DEFAULT_THRESHOLDS
    assert t.spend_velocity_min > 1.0
    assert 0 < t.category_shift_min < 1.0
    assert 0 < t.decline_rate_7d_min < 1.0
    assert t.large_transaction_amount_min > 0
    assert t.min_txn_count_7d >= 1


def test_thresholds_are_overridable():
    custom = MonitoringThresholds(spend_velocity_min=3.5, decline_rate_7d_min=0.25)
    assert custom.spend_velocity_min == 3.5
    assert custom.decline_rate_7d_min == 0.25
    assert custom.category_shift_min == DEFAULT_THRESHOLDS.category_shift_min


def test_summarize_respects_activity_floor():
    kpis = pd.DataFrame(
        {
            "as_of_date": ["2025-12-31", "2025-12-31"],
            "spend_velocity": [5.0, 5.0],
            "category_shift_score": [0.9, 0.9],
            "decline_rate_7d": [0.5, 0.5],
            "txn_count_7d": [1, 5],
        }
    )
    thresholds = MonitoringThresholds(
        spend_velocity_min=2.0,
        category_shift_min=0.35,
        decline_rate_7d_min=0.15,
        min_txn_count_7d=3,
    )
    summary = summarize_spend_kpis(kpis, thresholds)
    assert summary["spend_velocity"]["share_at_or_above_threshold"] == 0.5


@pytest.mark.skipif(
    not config.DUCKDB_PATH.is_file(),
    reason="DuckDB warehouse not built in this environment",
)
def test_load_spend_kpis_from_warehouse():
    con = connect()
    try:
        require_marts(con)
        df = load_spend_kpis(con=con)
    except RuntimeError:
        pytest.skip("dbt marts not built; run make dbt-run")
    finally:
        con.close()

    assert len(df) > 0
    for col in (
        "customer_id",
        "spend_velocity",
        "category_shift_score",
        "decline_rate_7d",
        "spend_7d",
        "spend_30d",
    ):
        assert col in df.columns
