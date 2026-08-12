# Credit Card Spend Anomaly Tracker

Local analytics platform for monitoring credit-card spend behavior, decline rates, and rule-based anomalies. Synthetic transaction data feeds a DuckDB warehouse transformed with dbt; alerts are detected deterministically and optionally narrated via local Ollama. A Streamlit dashboard reads those analytical outputs for monitoring.

This is a **synthetic transaction monitoring prototype**, not a production banking platform.

---

## Overview

The system generates realistic synthetic card transactions, loads them into DuckDB, models spend KPIs in dbt, detects anomalies with deterministic rules, optionally narrates alerts with a local Gemma model through Ollama, and serves a Streamlit risk-monitoring UI that consumes DuckDB marts and alert tables (no KPI recalculation in the UI).

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
Streamlit monitoring dashboard  ← reads DuckDB marts + alert tables
```

Details and trade-offs: see [DECISIONS.md](DECISIONS.md).

## Data Flow

1. `make generate-data` — synthetic customers/transactions → `data/raw/`
2. `make ingest` — load CSVs → DuckDB `raw_customers` / `raw_transactions`
3. `make dbt-run` — staging + marts in `database/spend_monitor.duckdb`
4. `make detect-anomalies` — rule-based alerts → `anomaly_alerts` + `data/processed/anomalies.csv`
5. `make narrate-anomalies` — narrations → `anomaly_alert_narrations` + `data/processed/anomalies_narrated.csv` (fallback text if Ollama is offline)
6. `make dashboard` — Streamlit UI over the warehouse (Ollama not required at startup)

## Data Model

| Layer | Role |
|-------|------|
| Raw | `raw_transactions`, `raw_customers` loaded from CSV |
| Staging | Typed, normalized `stg_transactions` |
| Marts | `mart_customer_spend`, `mart_spend_kpis`, `mart_decline_rates` |
| KPI layer | Python access to marts + monitoring thresholds (`kpi/`) |
| Alerts | `anomaly_alerts`, `anomaly_alert_narrations` |

## KPI Definitions

See [docs/kpi_definitions.md](docs/kpi_definitions.md) for full formulas. Summary:

1. **Spend velocity** — `spend_7d / (spend_30d × 7/30)`
2. **Category shift** — max absolute category-share change (recent 7d vs prior 30d baseline)
3. **Decline rate** — Declined / total transactions (7d, 30d, and weekly dimensional views)

Monitoring thresholds (business rules, not ML scores): [docs/anomaly_thresholds.md](docs/anomaly_thresholds.md). Implemented in `kpi/thresholds.py`. Inspect coverage with `make kpi-summary`.

## Anomaly Detection

Rule-based detection in `anomaly/detector.py` over `mart_spend_kpis` /
`mart_customer_spend`. Alert types: spend velocity, category shift, decline
rate, large transaction. Each alert stores `metric_value`, `threshold_value`,
and JSON `explanation_context`. Severity (LOW/MEDIUM/HIGH) combines breach
magnitude with multi-signal coincidence — see
[docs/severity.md](docs/severity.md). Thresholds:
[docs/anomaly_thresholds.md](docs/anomaly_thresholds.md).

## AI Narration

Ollama + a configurable Gemma-family model narrate alerts from structured
evidence only (`ai_narration/`). If Ollama is unavailable, a deterministic
fallback narration is used so the dashboard can still show text. Details:
[docs/ai_narration.md](docs/ai_narration.md).

**Ollama is optional.** Detection and the dashboard do not require it. When offline, every alert uses `narration_source=fallback`.

## Dashboard

Streamlit app at `dashboard/app.py` reads DuckDB marts and anomaly tables via `dashboard/data_access.py`. It does not redefine KPIs.

Views:

1. **Executive overview** — customers monitored, transaction volume, approved spend, decline rate, anomaly count, high-severity count
2. **KPI monitoring** — spend velocity, category shift, and decline-rate distributions from `mart_spend_kpis`, plus weekly portfolio decline from `mart_decline_rates`
3. **Anomaly alert feed** — timestamp, customer, type, severity, metric, threshold, evidence, narration; filters for severity / type / customer
4. **Customer drilldown** — spend trend, category mix, decline behavior, anomaly history, existing narration/evidence
5. **LLM status** — sidebar shows Ollama availability; offline mode uses fallback narration without crashing

```bash
make dashboard
# equivalent:
streamlit run dashboard/app.py --server.port=8501
```

Open http://localhost:8501. Generate the warehouse first (`make generate-data` through `make narrate-anomalies`).

## Docker

Local containerization for reproducibility. This is **not** a production deployment.

The image installs Python dependencies and application code. Generated DuckDB/CSV artifacts are **mounted at runtime** (not baked into the image). Ollama remains an external host dependency; the container points at `host.docker.internal:11434` and falls back to deterministic narration if unreachable.

```bash
# Build image
docker compose build

# Start dashboard (requires existing ./database and ./data from the pipeline)
docker compose up -d

# Open http://localhost:8501
docker compose logs -f dashboard
docker compose restart dashboard
docker compose down
```

Manual equivalent:

```bash
docker build -t spend-anomaly-dashboard:local .
docker run --rm -p 8501:8501 \
  -e DUCKDB_PATH=/app/database/spend_monitor.duckdb \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -v "$(pwd)/database:/app/database:ro" \
  -v "$(pwd)/data:/app/data:ro" \
  --add-host=host.docker.internal:host-gateway \
  spend-anomaly-dashboard:local
```

## Local Setup

**Prerequisites:** Python 3.11+, Git, Make. Optional: [Ollama](https://ollama.com) with a Gemma model for narration. Optional: Docker Desktop / Docker Engine for the containerized dashboard.

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
make generate-data     # synthetic customers + transactions → data/raw/
make ingest            # load CSVs → DuckDB raw_transactions / raw_customers
make dbt-run           # build staging + marts
make dbt-test          # dbt data tests
make kpi-summary       # KPI mart coverage vs monitoring thresholds
make detect-anomalies  # rule-based alerts → data/processed/anomalies.csv
make narrate-anomalies # Ollama narration (fallback if offline)
make dashboard         # Streamlit UI on http://localhost:8501
```

Equivalent without Make (from repo root):

```bash
python -m data_generator.generate_transactions
python -m ingestion.load_to_duckdb
dbt run --project-dir dbt --profiles-dir dbt
dbt test --project-dir dbt --profiles-dir dbt
python -m kpi.summarize
python -m anomaly.detector
python -m ai_narration.narrator
streamlit run dashboard/app.py --server.port=8501
```

Set `DUCKDB_PATH` to the absolute warehouse path if you are not using Make (Make exports it automatically).

## Testing

```bash
pytest
make dbt-clean   # run from repo root; do not use dbt clean --project-dir from root
make dbt-test
```

Dashboard logic tests live in `tests/test_dashboard.py` (data loading, filtering, overview reconciliation against DuckDB).

## Project Structure

```
data_generator/   Synthetic transaction generation
ingestion/        CSV → DuckDB raw load
dbt/              Staging and mart models
kpi/              Mart access + monitoring thresholds
anomaly/          Rule-based detection and severity scoring
ai_narration/     Ollama prompt + narration (fallback if offline)
dashboard/        Streamlit risk monitoring UI
data/             Raw and processed files (not committed)
database/         Local DuckDB file (not committed)
tests/            Unit and integration tests
docs/             Supplemental documentation
config.py         Shared paths and infrastructure settings
Dockerfile        Dashboard image
docker-compose.yml  Local dashboard service + volume mounts
```

## Design Decisions

See [DECISIONS.md](DECISIONS.md). KPI formulas: [docs/kpi_definitions.md](docs/kpi_definitions.md). Thresholds: [docs/anomaly_thresholds.md](docs/anomaly_thresholds.md). Severity: [docs/severity.md](docs/severity.md). Narration: [docs/ai_narration.md](docs/ai_narration.md).

## Status

Analytics pipeline through AI narration is implemented. Streamlit dashboard and local Docker packaging are implemented. Ollama remains optional.
