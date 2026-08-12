# Resume & LinkedIn Bullets

Copy and adapt. Keep wording factual — scale is ~50k synthetic transactions on a laptop.

## Strong bullets (preferred)

- Designed and built a local credit-card **spend monitoring** pipeline: synthetic generation → DuckDB → dbt staging/marts → rule-based anomaly alerts with severity → optional local LLM narration → Streamlit dashboard.
- Defined spend velocity, category-shift, and decline-rate KPIs in **dbt SQL** so Python and the UI consume a single metric layer instead of recalculating business logic.
- Implemented **deterministic anomaly detection** with documented thresholds, JSON evidence per alert, and severity scoring from breach magnitude and multi-signal coincidence.
- Integrated **Ollama/Gemma narration** that explains alert evidence only, with a deterministic fallback when the model is unavailable so monitoring never depends on the LLM being up.
- Shipped a Streamlit **risk-monitoring UI** (executive overview, KPI distributions, filterable alert feed, customer drilldown) reconciled to DuckDB totals; packaged with Docker Compose for local reproducibility.
- Added automated coverage with **dbt data tests** and **pytest**, including dashboard data-access and overview reconciliation checks.

## Shorter LinkedIn / summary lines

- End-to-end analytics prototype for card spend anomaly monitoring (DuckDB, dbt, Python rules, Streamlit, optional Ollama).
- Emphasis on explainable thresholds, evidence-backed alerts, and LLM-as-narrator — not LLM-as-detector.

## Phrases to avoid

| Avoid | Prefer |
|-------|--------|
| Fraud detection platform | Spend / decline anomaly monitoring |
| Real-time detection | Batch / laptop-scale pipeline |
| Production banking system | Synthetic monitoring prototype |
| Reduced fraud by X% | Surface explainable alerts with evidence |
| Millions of transactions | ~50k synthetic transactions (seeded) |
| AI detects anomalies | Rules detect; LLM narrates |

## Role targeting tips

- **Analytics Engineer** — lead with dbt models, tests, marts, DuckDB, Makefile reproducibility.
- **Data Analyst / Risk Analyst** — lead with KPI definitions, thresholds, dashboard drilldown, reconciliation.
- **Data Engineer** — lead with ingestion, warehouse layers, Docker, pipeline orchestration via Make.
- **AI-curious analyst roles** — lead with evidence-grounded narration and fallback behavior, not model training.
