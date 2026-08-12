"""Plotly charts for KPI and customer views."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Restrained fintech palette (no purple / neon)
COLOR_PRIMARY = "#1F4E79"
COLOR_SECONDARY = "#5B7C99"
COLOR_ACCENT = "#0F766E"
COLOR_MUTED = "#94A3B8"
COLOR_HIGH = "#B45309"
COLOR_MEDIUM = "#A16207"
COLOR_LOW = "#64748B"


def kpi_distribution_hist(series: pd.Series, title: str, x_label: str) -> go.Figure:
    clean = series.dropna()
    fig = px.histogram(
        clean,
        nbins=40,
        title=title,
        labels={"value": x_label, "count": "Customers"},
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=48, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        font=dict(family="Source Sans 3, Segoe UI, sans-serif", color="#0F172A"),
        showlegend=False,
        height=280,
    )
    fig.update_xaxes(gridcolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#E2E8F0")
    return fig


def weekly_decline_line(weekly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not weekly.empty:
        fig.add_trace(
            go.Scatter(
                x=weekly["period_start"],
                y=weekly["decline_rate"],
                mode="lines+markers",
                line=dict(color=COLOR_ACCENT, width=2),
                marker=dict(size=6),
                name="Decline rate",
            )
        )
    fig.update_layout(
        title="Portfolio weekly decline rate",
        margin=dict(l=20, r=20, t=48, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        font=dict(family="Source Sans 3, Segoe UI, sans-serif", color="#0F172A"),
        yaxis_tickformat=".1%",
        height=280,
    )
    fig.update_xaxes(gridcolor="#E2E8F0", title="Week start")
    fig.update_yaxes(gridcolor="#E2E8F0", title="Decline rate")
    return fig


def customer_spend_trend(transactions: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if transactions.empty:
        fig.update_layout(title="Daily approved spend", height=280)
        return fig

    approved = transactions[transactions["transaction_status"] == "Approved"].copy()
    if approved.empty:
        fig.update_layout(title="Daily approved spend (no approved activity)", height=280)
        return fig

    daily = (
        approved.groupby("transaction_date", as_index=False)["transaction_amount"]
        .sum()
        .sort_values("transaction_date")
    )
    fig.add_trace(
        go.Scatter(
            x=daily["transaction_date"],
            y=daily["transaction_amount"],
            mode="lines",
            line=dict(color=COLOR_PRIMARY, width=2),
            fill="tozeroy",
            fillcolor="rgba(31,78,121,0.12)",
            name="Approved spend",
        )
    )
    fig.update_layout(
        title="Daily approved spend",
        margin=dict(l=20, r=20, t=48, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        font=dict(family="Source Sans 3, Segoe UI, sans-serif", color="#0F172A"),
        height=280,
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#E2E8F0", title="USD")
    return fig


def customer_category_mix(transactions: pd.DataFrame) -> go.Figure:
    approved = transactions[transactions["transaction_status"] == "Approved"]
    if approved.empty:
        fig = go.Figure()
        fig.update_layout(title="Approved spend by category", height=280)
        return fig

    mix = (
        approved.groupby("merchant_category", as_index=False)["transaction_amount"]
        .sum()
        .sort_values("transaction_amount", ascending=True)
    )
    fig = px.bar(
        mix,
        x="transaction_amount",
        y="merchant_category",
        orientation="h",
        title="Approved spend by category",
        labels={"transaction_amount": "USD", "merchant_category": ""},
        color_discrete_sequence=[COLOR_SECONDARY],
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=48, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        font=dict(family="Source Sans 3, Segoe UI, sans-serif", color="#0F172A"),
        height=320,
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="#E2E8F0")
    return fig


def severity_color(severity: str) -> str:
    return {
        "HIGH": COLOR_HIGH,
        "MEDIUM": COLOR_MEDIUM,
        "LOW": COLOR_LOW,
    }.get(severity, COLOR_MUTED)
