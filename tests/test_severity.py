"""Tests for explainable severity scoring."""

from __future__ import annotations

import pandas as pd

from anomaly.severity import (
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    apply_severity,
    magnitude_severity,
)


def test_magnitude_severity_bands():
    assert magnitude_severity(2.0, 2.0) == SEVERITY_LOW
    assert magnitude_severity(3.0, 2.0) == SEVERITY_MEDIUM
    assert magnitude_severity(4.0, 2.0) == SEVERITY_HIGH


def test_multi_signal_boosts_one_level():
    frame = pd.DataFrame(
        [
            {
                "customer_id": "C1",
                "anomaly_type": "spend_velocity",
                "metric_value": 2.1,
                "threshold_value": 2.0,
            },
            {
                "customer_id": "C1",
                "anomaly_type": "category_shift",
                "metric_value": 0.36,
                "threshold_value": 0.35,
            },
            {
                "customer_id": "C2",
                "anomaly_type": "decline_rate",
                "metric_value": 0.16,
                "threshold_value": 0.15,
            },
        ]
    )
    scored = apply_severity(frame)
    c1 = scored[scored["customer_id"] == "C1"]
    c2 = scored[scored["customer_id"] == "C2"]
    # Base LOW (ratio ~1.05) bumped to MEDIUM when two signals present
    assert set(c1["severity"]) == {SEVERITY_MEDIUM}
    assert list(c2["severity"]) == [SEVERITY_LOW]


def test_three_signals_force_high():
    frame = pd.DataFrame(
        [
            {
                "customer_id": "C9",
                "anomaly_type": "spend_velocity",
                "metric_value": 2.1,
                "threshold_value": 2.0,
            },
            {
                "customer_id": "C9",
                "anomaly_type": "category_shift",
                "metric_value": 0.36,
                "threshold_value": 0.35,
            },
            {
                "customer_id": "C9",
                "anomaly_type": "decline_rate",
                "metric_value": 0.16,
                "threshold_value": 0.15,
            },
        ]
    )
    scored = apply_severity(frame)
    assert set(scored["severity"]) == {SEVERITY_HIGH}
