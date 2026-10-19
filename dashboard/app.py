"""Credit Card Spend Anomaly Tracker — risk monitoring dashboard.

Reads DuckDB marts and anomaly outputs. Does not recalculate KPI definitions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow `streamlit run dashboard/app.py` from repo root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_narration.narrator import ollama_available
from dashboard.components.charts import (
    customer_category_mix,
    customer_spend_trend,
    kpi_distribution_hist,
    weekly_decline_line,
)
from dashboard.components.formatting import format_currency, format_number, format_pct
from dashboard import data_access
import config

st.set_page_config(
    page_title="Spend Anomaly Monitor",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@600&display=swap');
      html, body, [class*="css"]  {
        font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        color: #0F172A;
      }
      .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1200px; }
      h1, h2, h3 {
        font-family: 'IBM Plex Serif', Georgia, serif !important;
        letter-spacing: -0.02em;
        color: #0B1F33 !important;
      }
      div[data-testid="stMetric"] {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 0.85rem 1rem;
        border-radius: 4px;
      }
      div[data-testid="stMetric"] label { color: #475569 !important; }
      section[data-testid="stSidebar"] {
        background: #0B1F33;
        color: #E2E8F0;
      }
      section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
      .status-pill {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 3px;
        font-size: 0.8rem;
        border: 1px solid #CBD5E1;
        background: #F1F5F9;
        color: #334155;
      }
      .status-ok { border-color: #99F6E4; background: #F0FDFA; color: #0F766E; }
      .status-warn { border-color: #FDE68A; background: #FFFBEB; color: #92400E; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _cached_overview(db_mtime: float) -> dict:
    return data_access.load_overview()


@st.cache_data(show_spinner=False)
def _cached_kpis(db_mtime: float) -> pd.DataFrame:
    return data_access.load_spend_kpis()


@st.cache_data(show_spinner=False)
def _cached_customers(db_mtime: float) -> pd.DataFrame:
    return data_access.load_customer_spend()


@st.cache_data(show_spinner=False)
def _cached_anomalies(db_mtime: float) -> pd.DataFrame:
    return data_access.load_anomalies()


@st.cache_data(show_spinner=False)
def _cached_weekly_decline(db_mtime: float) -> pd.DataFrame:
    return data_access.weekly_decline_trend()


@st.cache_data(show_spinner=False)
def _cached_customer_tx(customer_id: str, db_mtime: float) -> pd.DataFrame:
    return data_access.load_customer_transactions(customer_id)


def _db_mtime() -> float:
    path = config.DUCKDB_PATH
    return path.stat().st_mtime if path.is_file() else 0.0


def render_sidebar() -> None:
    st.sidebar.markdown("### Spend Anomaly Monitor")
    st.sidebar.caption("Internal risk monitoring · synthetic portfolio")
    llm_up = ollama_available(timeout_seconds=1.0)
    if llm_up:
        st.sidebar.markdown(
            '<span class="status-pill status-ok">Ollama available</span>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<span class="status-pill status-warn">Ollama offline · using fallback narration</span>',
            unsafe_allow_html=True,
        )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Warehouse\n`{config.DUCKDB_PATH.name}`")


def render_overview(overview: dict) -> None:
    st.subheader("Executive overview")
    as_of = overview.get("as_of_date")
    st.caption(f"KPI as-of date: {as_of}" if as_of is not None else "KPI as-of date unavailable")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Customers monitored", format_number(overview["customers_monitored"]))
    c2.metric("Transaction volume", format_number(overview["transaction_volume"]))
    c3.metric("Approved spend", format_currency(overview["total_approved_spend"]))
    c4.metric("Decline rate", format_pct(overview["decline_rate"]))
    c5.metric("Anomaly alerts", format_number(overview["anomaly_count"]))
    c6.metric("High severity", format_number(overview["high_severity_anomaly_count"]))


def render_kpi_section(kpis: pd.DataFrame, weekly: pd.DataFrame) -> None:
    st.subheader("KPI monitoring")
    st.caption(
        "Distributions from `mart_spend_kpis` and weekly decline from "
        "`mart_decline_rates` — definitions unchanged from dbt."
    )
    if kpis.empty:
        st.info("No KPI rows available. Run `make dbt-run`.")
        return

    left, mid, right = st.columns(3)
    with left:
        st.plotly_chart(
            kpi_distribution_hist(kpis["spend_velocity"], "Spend velocity", "Velocity"),
            width="stretch",
        )
        st.caption("7-day spend ÷ (30-day spend × 7/30)")
    with mid:
        st.plotly_chart(
            kpi_distribution_hist(
                kpis["category_shift_score"], "Category shift", "Max share change"
            ),
            width="stretch",
        )
        st.caption("Max |recent share − baseline share|")
    with right:
        st.plotly_chart(
            kpi_distribution_hist(kpis["decline_rate_7d"], "7-day decline rate", "Rate"),
            width="stretch",
        )
        st.caption("Declined ÷ total attempts (7-day window)")

    st.plotly_chart(weekly_decline_line(weekly), width="stretch")


def render_anomaly_feed(anomalies: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Anomaly alert feed")
    if anomalies.empty:
        st.info("No anomaly alerts loaded. Run `make detect-anomalies` (and optionally `make narrate-anomalies`).")
        return anomalies

    severities = sorted(anomalies["severity"].dropna().unique().tolist())
    types = sorted(anomalies["anomaly_type"].dropna().unique().tolist())
    customers = ["All"] + sorted(anomalies["customer_id"].dropna().unique().tolist())

    f1, f2, f3 = st.columns(3)
    selected_sev = f1.multiselect("Severity", severities, default=severities)
    selected_types = f2.multiselect("Anomaly type", types, default=types)
    selected_customer = f3.selectbox("Customer", customers)

    filtered = data_access.filter_anomalies(
        anomalies,
        severities=selected_sev,
        anomaly_types=selected_types,
        customer_id=selected_customer,
    )

    st.caption(f"{len(filtered):,} alerts after filters (of {len(anomalies):,})")
    if filtered.empty:
        st.warning("No alerts match the current filters.")
        return filtered

    display_cols = [
        c
        for c in [
            "detected_timestamp",
            "customer_id",
            "anomaly_type",
            "severity",
            "metric_value",
            "threshold_value",
            "explanation_context",
            "narration",
            "narration_source",
        ]
        if c in filtered.columns
    ]
    st.dataframe(
        filtered[display_cols],
        width="stretch",
        hide_index=True,
        height=360,
    )

    with st.expander("Selected alert detail", expanded=False):
        ids = filtered["anomaly_id"].tolist() if "anomaly_id" in filtered.columns else []
        if not ids:
            st.write("No anomaly IDs available.")
        else:
            chosen = st.selectbox("Alert ID", ids)
            row = filtered[filtered["anomaly_id"] == chosen].iloc[0]
            st.write(
                {
                    "customer_id": row.get("customer_id"),
                    "anomaly_type": row.get("anomaly_type"),
                    "severity": row.get("severity"),
                    "metric_value": row.get("metric_value"),
                    "threshold_value": row.get("threshold_value"),
                    "explanation_context": row.get("explanation_context"),
                    "narration": row.get("narration") or "No narration available",
                    "narration_source": row.get("narration_source") or "—",
                }
            )
    return filtered


def render_customer_drilldown(
    customers: pd.DataFrame,
    anomalies: pd.DataFrame,
    db_mtime: float,
) -> None:
    st.subheader("Customer drilldown")
    if customers.empty:
        st.info("No customer spend mart rows available.")
        return

    options = customers["customer_id"].tolist()
    default_idx = 0
    if not anomalies.empty:
        top = (
            anomalies.groupby("customer_id")
            .size()
            .sort_values(ascending=False)
            .index.tolist()
        )
        if top and top[0] in options:
            default_idx = options.index(top[0])

    customer_id = st.selectbox("Select customer", options, index=default_idx)
    profile = customers[customers["customer_id"] == customer_id].iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Card type", profile["card_type"])
    m2.metric("Approved spend", format_currency(float(profile["total_approved_spend"])))
    m3.metric("Decline rate", format_pct(float(profile["decline_rate"])))
    m4.metric("Top category", str(profile.get("top_category") or "—"))

    tx = _cached_customer_tx(customer_id, db_mtime)
    if tx.empty:
        st.warning("No transactions found for this customer.")
    else:
        left, right = st.columns(2)
        left.plotly_chart(customer_spend_trend(tx), width="stretch")
        right.plotly_chart(customer_category_mix(tx), width="stretch")

        decline_daily = (
            tx.groupby("transaction_date")
            .agg(
                attempts=("transaction_id", "count"),
                declined=("transaction_status", lambda s: (s == "Declined").sum()),
            )
            .reset_index()
        )
        decline_daily["decline_rate"] = decline_daily["declined"] / decline_daily["attempts"]
        st.caption("Decline behavior (daily attempt rate)")
        st.dataframe(
            decline_daily.tail(21),
            width="stretch",
            hide_index=True,
            height=220,
        )

    history = data_access.filter_anomalies(anomalies, customer_id=customer_id)
    st.markdown("**Anomaly history**")
    if history.empty:
        st.info("No anomalies for this customer.")
    else:
        cols = [
            c
            for c in [
                "detected_timestamp",
                "anomaly_type",
                "severity",
                "metric_value",
                "threshold_value",
                "explanation_context",
                "narration",
            ]
            if c in history.columns
        ]
        st.dataframe(history[cols], width="stretch", hide_index=True)


def main() -> None:
    render_sidebar()
    st.title("Credit Card Spend Anomaly Tracker")
    st.caption(
        "Synthetic transaction monitoring prototype · deterministic detection · optional local narration"
    )

    if not config.DUCKDB_PATH.is_file():
        st.error(
            f"DuckDB warehouse not found at `{config.DUCKDB_PATH}`. "
            "Run `make generate-data && make ingest && make dbt-run && make detect-anomalies`."
        )
        return

    db_mtime = _db_mtime()
    try:
        overview = _cached_overview(db_mtime)
        kpis = _cached_kpis(db_mtime)
        customers = _cached_customers(db_mtime)
        anomalies = _cached_anomalies(db_mtime)
        weekly = _cached_weekly_decline(db_mtime)
    except (FileNotFoundError, RuntimeError) as exc:
        st.error(str(exc))
        return

    render_overview(overview)
    st.markdown("---")
    render_kpi_section(kpis, weekly)
    st.markdown("---")
    render_anomaly_feed(anomalies)
    st.markdown("---")
    render_customer_drilldown(customers, anomalies, db_mtime)


if __name__ == "__main__":
    main()
