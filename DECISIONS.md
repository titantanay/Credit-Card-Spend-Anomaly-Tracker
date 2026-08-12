# Architecture Decisions

Concise record of choices for the Credit Card Spend Anomaly Tracker. Expanded as the system grows.

---

## 1. Why DuckDB?

Local analytical SQL without standing up a warehouse. Fits a laptop-sized prototype (~50k transactions), embeds cleanly in Python, and keeps the stack free of cloud credentials.

## 2. Why dbt?

Separates transformation from application code, gives versioned models and tests, and documents the path from raw → staging → marts the way an analytics engineering team would maintain it.

## 3. Why rule-based detection first?

Thresholds are explainable to risk analysts and easy to tune. Opaque ML classifiers add training data, evaluation, and ops cost that this prototype does not need. Rules can be replaced or supplemented later if labeled outcomes exist.

## 4. Why local Gemma / Ollama?

Narration without paid APIs or sending transaction context off-machine. Model name and endpoint are configuration, not hardcoded call sites. The dashboard degrades when Ollama is down.

## 5. Why Streamlit?

Fast path to an internal monitoring UI with Python-native data access. Adequate for analyst workflows; not positioned as a customer-facing product shell.

## 6. Why synthetic data?

No real cardholder data in a portfolio repo. Synthetic generation with seeded randomness keeps demos reproducible and lets us inject known behavioral patterns for detection.

## 7. Why the LLM does not make anomaly decisions?

LLMs can invent numbers and overstate certainty. Detection stays deterministic so every alert has metric value, threshold, and type. The model only writes prose from that evidence.

## 8. Why avoid unnecessary ML complexity?

The goal is a maintainable analytics pipeline (SQL, KPIs, rules, documentation), not a model zoo. Extra libraries and training loops would dilute the signal for a Senior Analyst / Analytics Engineer portfolio.

## 9. How this could migrate to a cloud warehouse later

Swap the DuckDB profile for BigQuery, Snowflake, or Redshift in dbt; keep staging/mart contracts and Python detection against warehouse tables or exported extracts. Generator and dashboard remain local or move behind the same SQL interfaces.

---

*Additional decisions will be appended as pipeline, KPI, and packaging choices are finalized.*
