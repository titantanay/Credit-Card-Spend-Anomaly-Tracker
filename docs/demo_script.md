# Demo Script (~8–10 minutes)

Assumes the warehouse already exists. If not, run the full pipeline first (see README).

## Setup (before the call)

```bash
source .venv/bin/activate   # or Windows equivalent
make generate-data && make ingest && make dbt-run && make dbt-test
make kpi-summary && make detect-anomalies && make narrate-anomalies
make dashboard
```

Optional Docker path (after pipeline artifacts exist):

```bash
docker compose up -d
# open http://localhost:8501
```

Ollama is optional. If it is offline, narration still appears via fallback — call that out as a feature.

## Walkthrough

### 1. Business framing (45s)

“This is a synthetic spend monitoring prototype for an analyst. We care about velocity spikes, category mix shifts, and elevated decline rates — with every alert tied to a metric and threshold.”

### 2. Architecture slide / README diagram (60s)

Generator → CSV → DuckDB → dbt marts → KPI thresholds → anomaly rules → narration → Streamlit.  
Emphasize: **SQL owns KPI math; the LLM does not decide alerts.**

### 3. Warehouse proof (90s)

```bash
make dbt-test
make kpi-summary
```

Mention: 46 dbt tests; marts for customer spend, spend KPIs, decline rates.

### 4. Anomaly + narration (90s)

```bash
# already run; show sample
head -n 3 data/processed/anomalies_narrated.csv
```

Point to columns: `anomaly_type`, `severity`, `metric_value`, `threshold_value`, `explanation_context`, `narration`, `narration_source`.  
If Ollama is down: `narration_source=fallback`.

### 5. Dashboard (3–4 min)

Open http://localhost:8501.

1. **Executive overview** — customers, volume, approved spend, decline rate, alert counts. State that these reconcile to DuckDB.
2. **KPI monitoring** — velocity / category-shift / decline distributions from marts.
3. **Anomaly feed** — filter HIGH only; open one alert; show evidence + narration.
4. **Customer drilldown** — pick a flagged customer; show spend trend, category mix, decline behavior, history.

### 6. Reproducibility close (45s)

```bash
pytest
docker compose ps   # if using containers
```

“Everything runs on a laptop without cloud APIs. Docker mounts the warehouse; Ollama stays on the host.”

## Numbers to keep handy (seed 42 portfolio)

| Metric | Value |
|--------|-------|
| Customers | 1,000 (998 with transactions) |
| Transactions | 50,000 |
| Approved / Declined | 46,957 / 3,043 |
| Decline rate | 6.09% |
| Approved spend | ~$7,975,800 |
| Anomaly alerts | 619 (230 HIGH) |
| Customers flagged | 449 |

If you regenerate with a different seed, update these numbers before the demo.

## Hard questions — short answers

- **Is this fraud detection?** No — behavioral spend/decline monitoring with explainable rules.
- **Would this scale?** The *contracts* (dbt marts, thresholds, evidence) migrate to a cloud warehouse; this repo optimizes for local clarity.
- **Why so many category-shift flags?** Synthetic mix + current threshold; documented as a calibration backlog, not a silent bug. See [limitations.md](limitations.md).
