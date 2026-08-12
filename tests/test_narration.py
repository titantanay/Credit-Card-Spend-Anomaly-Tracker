"""Tests for anomaly narration prompts and Ollama client behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from ai_narration.narrator import narrate_alert, narrate_anomalies, ollama_available
from ai_narration.prompts import build_user_prompt, fallback_narration


def _sample_alert(**overrides):
    alert = {
        "anomaly_id": "A000001",
        "customer_id": "C0001",
        "card_type": "Gold",
        "anomaly_type": "spend_velocity",
        "severity": "HIGH",
        "metric_value": 3.2,
        "threshold_value": 2.0,
        "as_of_date": "2025-12-31",
        "explanation_context": (
            '{"rule": "spend_7d / (spend_30d * 7/30) >= threshold", '
            '"spend_7d": 900.0, "spend_30d": 900.0, "txn_count_7d": 5}'
        ),
    }
    alert.update(overrides)
    return alert


def test_user_prompt_includes_evidence_not_fraud_language():
    prompt = build_user_prompt(_sample_alert())
    assert "C0001" in prompt
    assert "spend_velocity" in prompt
    assert "3.2" in prompt
    assert "2.0" in prompt
    assert "fraud" not in prompt.lower()


def test_fallback_narration_is_grounded():
    text = fallback_narration(_sample_alert())
    assert "C0001" in text
    assert "3.20" in text
    assert "2.00" in text
    assert "HIGH" in text
    assert "fraud" not in text.lower()


def test_fallback_category_shift_mentions_driver():
    text = fallback_narration(
        _sample_alert(
            anomaly_type="category_shift",
            metric_value=0.4,
            threshold_value=0.35,
            explanation_context='{"category_shift_driver": "Travel", "txn_count_7d": 6}',
        )
    )
    assert "Travel" in text
    assert "0.40" in text


@patch("ai_narration.narrator.requests.get")
def test_ollama_available_false_on_connection_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("down")
    assert ollama_available() is False


@patch("ai_narration.narrator.requests.post")
def test_narrate_alert_uses_ollama_when_requested(mock_post):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "content": (
                "Customer spending increased substantially above their recent "
                "baseline. The change should be reviewed for abnormal activity."
            )
        }
    }
    mock_post.return_value = mock_response

    result = narrate_alert(_sample_alert(), use_ollama=True)
    assert result["narration_source"] == "ollama"
    assert "baseline" in result["narration"]
    assert mock_post.called
    sent = mock_post.call_args.kwargs["json"]
    assert sent["messages"][0]["role"] == "system"
    assert "C0001" in sent["messages"][1]["content"]


@patch("ai_narration.narrator.ollama_available", return_value=False)
def test_narrate_anomalies_falls_back_when_ollama_down(_mock_available):
    frame = pd.DataFrame([_sample_alert(), _sample_alert(anomaly_id="A000002")])
    narrated = narrate_anomalies(frame)
    assert list(narrated["narration_source"]) == ["fallback", "fallback"]
    assert narrated["narration"].str.contains("C0001").all()
