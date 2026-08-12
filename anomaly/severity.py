"""Explainable anomaly severity: LOW / MEDIUM / HIGH.

Severity is derived from (1) how far the metric exceeds its threshold and
(2) whether the same customer has multiple alert types in the run.
No opaque scores — analysts can recompute the label from stored fields.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_ORDER = (SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH)


@dataclass(frozen=True)
class SeverityRules:
    """Configurable cutovers for magnitude and multi-signal boosts."""

    # metric / threshold ratios for a single alert
    medium_ratio: float = 1.5
    high_ratio: float = 2.0

    # distinct anomaly_type count for the same customer in one detection run
    multi_signal_boost_at: int = 2
    multi_signal_high_at: int = 3


DEFAULT_SEVERITY_RULES = SeverityRules()


def magnitude_severity(
    metric_value: float,
    threshold_value: float,
    rules: SeverityRules = DEFAULT_SEVERITY_RULES,
) -> str:
    """Map breach magnitude to a base severity."""
    if threshold_value <= 0:
        return SEVERITY_MEDIUM
    ratio = metric_value / threshold_value
    if ratio >= rules.high_ratio:
        return SEVERITY_HIGH
    if ratio >= rules.medium_ratio:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def _bump(severity: str, steps: int = 1) -> str:
    idx = SEVERITY_ORDER.index(severity)
    return SEVERITY_ORDER[min(idx + steps, len(SEVERITY_ORDER) - 1)]


def apply_severity(
    anomalies: pd.DataFrame,
    rules: SeverityRules = DEFAULT_SEVERITY_RULES,
) -> pd.DataFrame:
    """Assign severity from magnitude, then raise for multi-signal customers.

    Multi-signal rules (same customer, same detection batch):
    - 2 distinct anomaly types → bump each alert one level
    - 3+ distinct anomaly types → HIGH on every alert for that customer
    """
    if anomalies.empty:
        return anomalies.copy()

    out = anomalies.copy()
    out["severity"] = [
        magnitude_severity(float(m), float(t), rules)
        for m, t in zip(out["metric_value"], out["threshold_value"], strict=True)
    ]

    type_counts = out.groupby("customer_id")["anomaly_type"].nunique()
    out["_signal_count"] = out["customer_id"].map(type_counts)

    boosted: list[str] = []
    for severity, signal_count in zip(out["severity"], out["_signal_count"], strict=True):
        if signal_count >= rules.multi_signal_high_at:
            boosted.append(SEVERITY_HIGH)
        elif signal_count >= rules.multi_signal_boost_at:
            boosted.append(_bump(severity, 1))
        else:
            boosted.append(severity)

    out["severity"] = boosted
    return out.drop(columns=["_signal_count"])
