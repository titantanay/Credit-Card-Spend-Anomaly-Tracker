"""Narrate detected anomalies via local Ollama (Gemma-family by default).

Analytics already decided the alert. This module only writes short prose from
structured evidence. If Ollama is down, a deterministic fallback is used so
downstream dashboards still have readable text.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import duckdb
import pandas as pd
import requests

import config
from ai_narration.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    fallback_narration,
)

NARRATION_COLUMNS = [
    "narration",
    "narration_source",  # ollama | fallback
]


def ollama_available(
    base_url: str | None = None,
    timeout_seconds: float = 2.0,
) -> bool:
    base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=timeout_seconds)
        return response.ok
    except requests.RequestException:
        return False


def _call_ollama(
    alert: Mapping[str, Any],
    *,
    base_url: str,
    model: str,
    timeout_seconds: float,
) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(alert)},
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 120,
        },
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/api/chat",
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    body = response.json()
    message = body.get("message") or {}
    text = (message.get("content") or "").strip()
    if not text:
        raise ValueError("Ollama returned an empty narration")
    # Keep analyst feed compact even if the model is verbose.
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    clipped = ". ".join(sentences[:2]).strip()
    if clipped and not clipped.endswith("."):
        clipped += "."
    return clipped


def narrate_alert(
    alert: Mapping[str, Any],
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 30.0,
    use_ollama: bool | None = None,
) -> dict[str, str]:
    base_url = base_url or config.OLLAMA_BASE_URL
    model = model or config.OLLAMA_MODEL
    if use_ollama is None:
        use_ollama = ollama_available(base_url=base_url)

    if use_ollama:
        try:
            text = _call_ollama(
                alert,
                base_url=base_url,
                model=model,
                timeout_seconds=timeout_seconds,
            )
            return {"narration": text, "narration_source": "ollama"}
        except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError):
            pass

    return {
        "narration": fallback_narration(alert),
        "narration_source": "fallback",
    }


def narrate_anomalies(
    anomalies: pd.DataFrame,
    *,
    base_url: str | None = None,
    model: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    if anomalies.empty:
        out = anomalies.copy()
        out["narration"] = pd.Series(dtype="string")
        out["narration_source"] = pd.Series(dtype="string")
        return out

    working = anomalies.copy()
    if limit is not None:
        working = working.head(limit)

    available = ollama_available(base_url=base_url)
    narrations: list[str] = []
    sources: list[str] = []
    for record in working.to_dict(orient="records"):
        result = narrate_alert(
            record,
            base_url=base_url,
            model=model,
            use_ollama=available,
        )
        narrations.append(result["narration"])
        sources.append(result["narration_source"])

    working["narration"] = narrations
    working["narration_source"] = sources
    return working


def persist_narrations(
    narrated: pd.DataFrame,
    csv_path: Path | None = None,
    duckdb_path: Path | None = None,
) -> Path:
    config.ensure_data_dirs()
    csv_path = csv_path or config.ANOMALIES_NARRATED_CSV
    duckdb_path = duckdb_path or config.DUCKDB_PATH

    narrated.to_csv(csv_path, index=False)

    if duckdb_path.is_file():
        con = duckdb.connect(str(duckdb_path))
        try:
            con.register("_narrated_df", narrated)
            con.execute(
                "create or replace table anomaly_alert_narrations as "
                "select * from _narrated_df"
            )
            con.unregister("_narrated_df")
        finally:
            con.close()

    return csv_path


def load_anomalies(csv_path: Path | None = None) -> pd.DataFrame:
    path = csv_path or config.ANOMALIES_CSV
    if not path.is_file():
        raise FileNotFoundError(
            f"Anomalies file not found: {path}. Run: make detect-anomalies"
        )
    return pd.read_csv(path)


def run(
    *,
    limit: int | None = None,
    csv_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    anomalies = load_anomalies(csv_path)
    narrated = narrate_anomalies(anomalies, limit=limit)
    persist_narrations(narrated, csv_path=output_path)
    return narrated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Narrate anomaly alerts with local Ollama (fallback if unavailable)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Narrate only the first N alerts (useful for local smoke tests)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Anomalies CSV (default: data/processed/anomalies.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Narrated CSV (default: data/processed/anomalies_narrated.csv)",
    )
    args = parser.parse_args()

    narrated = run(limit=args.limit, csv_path=args.input, output_path=args.output)
    sources = narrated["narration_source"].value_counts().to_dict() if len(narrated) else {}
    out = args.output or config.ANOMALIES_NARRATED_CSV
    print(f"Wrote {len(narrated):,} narrated alerts → {out}")
    print(f"Sources: {sources}")
    if len(narrated):
        print("Example:")
        print(f"  {narrated.iloc[0]['anomaly_id']}: {narrated.iloc[0]['narration']}")


if __name__ == "__main__":
    main()
