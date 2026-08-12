"""Configurable monitoring thresholds for spend KPIs.

These are business rules, not model scores. Phase 7 anomaly detection will
consume this module; values are intentionally easy to change in one place.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MonitoringThresholds:
    """Rules that mark a KPI reading as elevated for analyst review.

    Defaults are chosen from the KPI definitions and the behavior of the
    synthetic portfolio (overall decline ~6%, velocity 1.0 = on-pace).
    Retune when moving to real card data.
    """

    # Weekly spend at least 2× the 30-day daily pace (spend_7d / (spend_30d×7/30)).
    # 1.0 is on-pace; 2.0 means an extra week of typical spend compressed into 7 days.
    spend_velocity_min: float = 2.0

    # Max absolute category-share change (recent 7d vs prior 30d baseline).
    # Aligns with the documented example: Travel 10% → 45% ⇒ 0.35.
    category_shift_min: float = 0.35

    # 7-day decline rate. Portfolio baseline is ~6%; 15% is roughly 2.5× that
    # level and requires multiple declines in an active week for sparse users
    # when combined with min_txn_count_7d.
    decline_rate_7d_min: float = 0.15

    # Absolute Approved ticket size (USD) treated as unusually large.
    # Above typical grocery/dining; within elevated travel/electronics range.
    large_transaction_amount_min: float = 1_500.0

    # Ignore ratio-based flags when the recent week has fewer attempts than this.
    # Prevents a single decline in a 1–2 transaction week from dominating.
    min_txn_count_7d: int = 3

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


# Single process-wide default. Override by constructing MonitoringThresholds(...).
DEFAULT_THRESHOLDS = MonitoringThresholds()
