"""Shared formatting helpers for the monitoring dashboard."""

from __future__ import annotations


def format_currency(value: float | None) -> str:
    if value is None:
        return "—"
    # Round to cents first so DuckDB float residue does not bump the dollar display.
    return f"${round(float(value), 2):,.0f}"


def format_pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}%"


def format_number(value: float | int | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}"
