# Credit Card Spend Anomaly Tracker

Local analytics platform for monitoring credit-card spend behavior, decline rates, and rule-based anomalies. Synthetic transaction data feeds a DuckDB warehouse transformed with dbt; a Streamlit dashboard surfaces alerts with optional local LLM narration via Ollama.

This is a **synthetic transaction monitoring prototype**, not a production banking platform.

---

## Overview

The system generates realistic synthetic card transactions, loads them into DuckDB, models spend KPIs in dbt, detects anomalies with deterministic rules, optionally narrates alerts with a local Gemma model through Ollama, and presents results in a risk-monitoring dashboard.

## Business Problem

Sudden changes in spend velocity, category mix, or decline rates can signal operational risk, card misuse, or customer distress. Analysts need a repeatable pipeline that measures behavior against baselines and preserves the numerical evidence behind every alert.

## Architecture

```
Python data generator
        ↓
    Raw CSV
        ↓
 DuckDB raw layer
        ↓
   dbt staging
        ↓
    dbt marts
        ↓
    KPI layer
        ↓
Python anomaly detection
        ↓
   Anomaly alerts
        ↓
Local LLM narration (Ollama)  ← optional; analytics decide, LLM explains
        ↓
Streamlit monitoring dashboard
```

Details and trade-offs: see [DECISIONS.md](DECISIONS.md).

## Data Model

| Layer | Role |
|-------|------|
| Raw | `raw_transactions`, `raw_customers` loaded from CSV |
| Staging | Typed, normalized `stg_transactions` |
| Marts | `mart_customer_spend`, `mart_spend_kpis`, `mart_decline_rates` |

## KPI Definitions

See [docs/kpi_definitions.md](docs/kpi_definitions.md) for full formulas. Summary:

1. **Spend velocity** — `spend_7d / (spend_30d × 7/30)`
2. **Category shift** — max absolute category-share change (recent 7d vs prior 30d baseline)
3. **Decline rate** — declined / total transactions (7d, 30d, and weekly dimensional views)

## Anomaly Detection

Rule-based detection over mart/KPI outputs. Thresholds are configurable business rules. The detector never relies on the LLM to decide whether behavior is anomalous.

## AI Narration

Ollama + a Gemma-family model produce short, analyst-facing explanations from structured anomaly evidence only. If Ollama is unavailable, the dashboard still runs.

## Dashboard

Internal risk view: executive overview, anomaly feed, customer drilldown, KPI trends. Reads from DuckDB/dbt outputs rather than recomputing from raw CSV.

## Local Setup

**Prerequisites:** Python 3.11+, Git. Optional: [Ollama](https://ollama.com) with a Gemma model for narration.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Pipeline commands:

```bash
make generate-data   # synthetic customers + transactions → data/raw/
make ingest          # load CSVs → DuckDB raw_transactions / raw_customers
make dbt-run         # build staging (and later marts)
make dbt-test        # dbt data tests
# make detect-anomalies / dashboard  (later phases)
```

Equivalent without Make (from repo root):

```bash
python -m data_generator.generate_transactions
python -m ingestion.load_to_duckdb
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
```

Set `DUCKDB_PATH` to the absolute warehouse path if you are not using Make (Make exports it automatically).

## Testing

```bash
pytest
make dbt-test
```

## Project Structure

```
data_generator/   Synthetic transaction generation
ingestion/        CSV → DuckDB raw load
dbt/              Staging and mart models
anomaly/          Rule-based detection and severity
ai_narration/     Ollama prompt + narration client
dashboard/        Streamlit risk monitoring UI
data/             Raw and processed files (not committed)
database/         Local DuckDB file (not committed)
tests/            Unit and integration tests
docs/             Supplemental documentation
config.py         Shared paths and infrastructure settings
```

## Design Decisions

See [DECISIONS.md](DECISIONS.md). KPI formulas: [docs/kpi_definitions.md](docs/kpi_definitions.md).

## Status

Phase 5 — dbt marts and KPI definitions. Anomaly detection and dashboard land in subsequent phases.
