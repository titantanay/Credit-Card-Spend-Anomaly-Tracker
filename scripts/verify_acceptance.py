#!/usr/bin/env python3
"""Stage 11 acceptance verifier for the default seeded portfolio.

Validates warehouse artifacts and reconciles headline metrics for seed=42
defaults (1,000 customers / 50,000 transactions). Exits non-zero on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb

import config
from dashboard.components.formatting import format_currency, format_pct
from dashboard.data_access import load_anomalies, load_overview


# Expected values for data_generator.config defaults + RANDOM_SEED=42.
EXPECTED = {
    "customers": 1_000,
    "customers_with_tx": 998,
    "transactions": 50_000,
    "approved": 46_957,
    "declined": 3_043,
    "decline_rate": 0.06086,
    "approved_spend": 7_975_800.5,
    "anomalies": 619,
    "high_severity": 230,
    "flagged_customers": 449,
    "narrations": 619,
}


def _check(name: str, cond: bool, detail: object = "") -> None:
    status = "PASS" if cond else "FAIL"
    suffix = f" ({detail})" if detail != "" else ""
    print(f"{status} - {name}{suffix}")
    if not cond:
        raise AssertionError(f"{name} failed{suffix}")


def main() -> int:
    _check("duckdb_exists", config.DUCKDB_PATH.is_file(), config.DUCKDB_PATH)
    _check("anomalies_csv", config.ANOMALIES_CSV.is_file())
    _check("anomalies_narrated_csv", config.ANOMALIES_NARRATED_CSV.is_file())
    _check("dashboard_app", (ROOT / "dashboard" / "app.py").is_file())
    _check("dockerfile", (ROOT / "Dockerfile").is_file())
    _check("compose", (ROOT / "docker-compose.yml").is_file())

    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        customers = con.execute("select count(*) from raw_customers").fetchone()[0]
        tx = con.execute(
            "select count(*) from staging.stg_transactions"
        ).fetchone()[0]
        approved = con.execute(
            "select count(*) from staging.stg_transactions "
            "where transaction_status = 'Approved'"
        ).fetchone()[0]
        declined = con.execute(
            "select count(*) from staging.stg_transactions "
            "where transaction_status = 'Declined'"
        ).fetchone()[0]
        spend = con.execute(
            "select coalesce(sum(total_approved_spend), 0) "
            "from marts.mart_customer_spend"
        ).fetchone()[0]
        cust_with_tx = con.execute(
            "select count(*) from marts.mart_customer_spend "
            "where transaction_count > 0"
        ).fetchone()[0]
        anom = con.execute("select count(*) from anomaly_alerts").fetchone()[0]
        high = con.execute(
            "select count(*) from anomaly_alerts where severity = 'HIGH'"
        ).fetchone()[0]
        flagged = con.execute(
            "select count(distinct customer_id) from anomaly_alerts"
        ).fetchone()[0]
        narr = con.execute(
            "select count(*) from anomaly_alert_narrations"
        ).fetchone()[0]
        grounded = con.execute(
            """
            select count(*) from anomaly_alert_narrations
            where narration is not null
              and length(trim(narration)) > 0
              and metric_value is not null
              and threshold_value is not null
            """
        ).fetchone()[0]
    finally:
        con.close()

    _check("customers", customers == EXPECTED["customers"], customers)
    _check(
        "customers_with_tx",
        cust_with_tx == EXPECTED["customers_with_tx"],
        cust_with_tx,
    )
    _check("transactions", tx == EXPECTED["transactions"], tx)
    _check("approved", approved == EXPECTED["approved"], approved)
    _check("declined", declined == EXPECTED["declined"], declined)
    _check(
        "decline_rate",
        abs(declined / tx - EXPECTED["decline_rate"]) < 1e-4,
        f"{100 * declined / tx:.2f}%",
    )
    _check(
        "approved_spend",
        abs(spend - EXPECTED["approved_spend"]) < 0.01,
        spend,
    )
    _check("anomalies", anom == EXPECTED["anomalies"], anom)
    _check("high_severity", high == EXPECTED["high_severity"], high)
    _check("flagged_customers", flagged == EXPECTED["flagged_customers"], flagged)
    _check("narrations", narr == EXPECTED["narrations"], narr)
    _check("narration_grounding", grounded == EXPECTED["narrations"], grounded)

    overview = load_overview()
    anomalies = load_anomalies()
    _check("dash_tx", overview["transaction_volume"] == tx)
    _check(
        "dash_spend",
        abs(overview["total_approved_spend"] - spend) < 0.01,
    )
    _check(
        "dash_decline",
        abs(overview["decline_rate"] - declined / tx) < 1e-9,
    )
    _check("dash_anom", overview["anomaly_count"] == anom)
    _check("dash_high", overview["high_severity_anomaly_count"] == high)
    _check(
        "dash_fmt_spend",
        format_currency(overview["total_approved_spend"]) == "$7,975,800",
    )
    _check(
        "dash_fmt_decline",
        format_pct(overview["decline_rate"]) == "6.09%",
    )
    _check("dash_anom_rows", len(anomalies) == anom)
    _check("dash_narration_present", anomalies["narration"].notna().all())

    print("---")
    print("verify_acceptance: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"verify_acceptance: FAILED — {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
