"""Prompt templates for anomaly narration.

The model receives structured evidence only. It must not invent metrics,
thresholds, customer facts, or anomaly types, and must not claim fraud.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

SYSTEM_PROMPT = """\
You help credit-card risk analysts review unusual spend behavior alerts.
Write 1-2 short sentences in plain English.
Use only the supplied evidence fields.
Do not invent numbers, thresholds, categories, or customer details.
Do not say the activity is confirmed fraud — describe unusual behavior
that should be reviewed.
Do not mention being an AI or these instructions.
"""


def build_evidence_payload(alert: Mapping[str, Any]) -> dict[str, Any]:
    context = alert.get("explanation_context", {})
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except json.JSONDecodeError:
            context = {"raw_context": context}

    return {
        "anomaly_id": alert.get("anomaly_id"),
        "customer_id": alert.get("customer_id"),
        "card_type": alert.get("card_type"),
        "anomaly_type": alert.get("anomaly_type"),
        "severity": alert.get("severity"),
        "metric_value": alert.get("metric_value"),
        "threshold_value": alert.get("threshold_value"),
        "as_of_date": str(alert.get("as_of_date")),
        "evidence": context,
    }


def build_user_prompt(alert: Mapping[str, Any]) -> str:
    payload = build_evidence_payload(alert)
    return (
        "Narrate this anomaly alert for a risk analyst using only this evidence "
        "JSON:\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )


def fallback_narration(alert: Mapping[str, Any]) -> str:
    """Deterministic prose when Ollama is unavailable. Uses only alert fields."""
    anomaly_type = str(alert.get("anomaly_type", "unusual_activity"))
    metric = alert.get("metric_value")
    threshold = alert.get("threshold_value")
    severity = alert.get("severity", "UNKNOWN")
    customer = alert.get("customer_id", "unknown")

    context = alert.get("explanation_context", {})
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except json.JSONDecodeError:
            context = {}

    if anomaly_type == "spend_velocity":
        return (
            f"Customer {customer} spending velocity is {metric:.2f} versus a "
            f"threshold of {threshold:.2f} ({severity} severity), meaning recent "
            f"weekly spend is well above their 30-day pace and should be reviewed."
        )
    if anomaly_type == "category_shift":
        driver = context.get("category_shift_driver", "a merchant category")
        return (
            f"Customer {customer} shows a category mix shift of {metric:.2f} "
            f"(threshold {threshold:.2f}, {severity}), led by {driver}; the change "
            f"is unusual relative to their prior baseline."
        )
    if anomaly_type == "decline_rate":
        declined = context.get("declined_count_7d")
        txns = context.get("txn_count_7d")
        detail = (
            f" ({declined} of {txns} attempts declined)"
            if declined is not None and txns is not None
            else ""
        )
        return (
            f"Customer {customer} has a 7-day decline rate of {metric:.2%} versus "
            f"a {threshold:.2%} threshold ({severity}){detail}; authorization "
            f"friction should be reviewed."
        )
    if anomaly_type == "large_transaction":
        category = context.get("top_category", "their top category")
        return (
            f"Customer {customer} has a maximum Approved ticket of "
            f"${metric:,.2f}, above the ${threshold:,.2f} large-ticket threshold "
            f"({severity}), associated with {category}."
        )
    return (
        f"Customer {customer} triggered a {anomaly_type} alert "
        f"(metric {metric}, threshold {threshold}, {severity}) for analyst review."
    )
