"""KPI coverage summary from mart tables (not anomaly detection)."""

from __future__ import annotations

import argparse
import json

import pandas as pd

from kpi.repository import load_customer_spend, load_spend_kpis
from kpi.thresholds import DEFAULT_THRESHOLDS, MonitoringThresholds


def summarize_spend_kpis(
    kpis: pd.DataFrame,
    thresholds: MonitoringThresholds = DEFAULT_THRESHOLDS,
) -> dict:
    if kpis.empty:
        return {"customers": 0}

    velocity = kpis["spend_velocity"]
    shift = kpis["category_shift_score"]
    decline = kpis["decline_rate_7d"]
    active = kpis["txn_count_7d"] >= thresholds.min_txn_count_7d

    return {
        "as_of_date": str(kpis["as_of_date"].iloc[0]),
        "customers": int(len(kpis)),
        "thresholds": thresholds.to_dict(),
        "spend_velocity": {
            "defined": int(velocity.notna().sum()),
            "mean": _round(velocity.mean()),
            "share_at_or_above_threshold": _round(
                ((velocity >= thresholds.spend_velocity_min) & active).mean()
            ),
        },
        "category_shift": {
            "mean": _round(shift.mean()),
            "share_at_or_above_threshold": _round(
                ((shift >= thresholds.category_shift_min) & active).mean()
            ),
        },
        "decline_rate_7d": {
            "mean": _round(decline.mean()),
            "share_at_or_above_threshold": _round(
                ((decline >= thresholds.decline_rate_7d_min) & active).mean()
            ),
        },
    }


def summarize_customer_spend(customers: pd.DataFrame) -> dict:
    if customers.empty:
        return {"customers": 0}
    large = customers["max_approved_amount"] >= DEFAULT_THRESHOLDS.large_transaction_amount_min
    return {
        "customers": int(len(customers)),
        "customers_with_transactions": int((customers["transaction_count"] > 0).sum()),
        "total_approved_spend": _round(customers["total_approved_spend"].sum()),
        "overall_decline_rate": _round(
            customers["declined_count"].sum()
            / max(customers["transaction_count"].sum(), 1)
        ),
        "share_with_large_ticket": _round(large.mean()),
    }


def _round(value: float | None) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return round(float(value), 4)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize KPI mart coverage against monitoring thresholds."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    args = parser.parse_args()

    kpis = load_spend_kpis()
    customers = load_customer_spend()
    report = {
        "spend_kpis": summarize_spend_kpis(kpis),
        "customer_spend": summarize_customer_spend(customers),
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return

    sk = report["spend_kpis"]
    cs = report["customer_spend"]
    th = sk["thresholds"]
    print(f"KPI as_of_date: {sk['as_of_date']}")
    print(f"Customers in KPI mart: {sk['customers']:,}")
    print(f"Customers in spend mart: {cs['customers']:,} "
          f"({cs['customers_with_transactions']:,} with transactions)")
    print(f"Total approved spend: {cs['total_approved_spend']:,}")
    print(f"Overall decline rate: {cs['overall_decline_rate']}")
    print()
    print("Thresholds (business rules):")
    for key, value in th.items():
        print(f"  {key}: {value}")
    print()
    print("Share of active customers (≥ min_txn_count_7d) at/above threshold:")
    print(f"  spend_velocity ≥ {th['spend_velocity_min']}: "
          f"{sk['spend_velocity']['share_at_or_above_threshold']}")
    print(f"  category_shift ≥ {th['category_shift_min']}: "
          f"{sk['category_shift']['share_at_or_above_threshold']}")
    print(f"  decline_rate_7d ≥ {th['decline_rate_7d_min']}: "
          f"{sk['decline_rate_7d']['share_at_or_above_threshold']}")
    print(f"  large ticket ≥ {th['large_transaction_amount_min']}: "
          f"{cs['share_with_large_ticket']}")


if __name__ == "__main__":
    main()
