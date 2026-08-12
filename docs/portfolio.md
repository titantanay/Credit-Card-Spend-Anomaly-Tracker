# Portfolio Positioning

Honest framing for resumes, interviews, and demos. This project is a **synthetic credit-card spend monitoring prototype**, not a production banking or fraud platform.

## One-line pitch

Built an end-to-end local analytics pipeline that turns synthetic card transactions into dbt marts, rule-based anomaly alerts with severity, optional LLM narration, and a Streamlit monitoring dashboard — with reproducible tests and Docker packaging.

## Problem → solution story (60–90 seconds)

1. **Problem** — Risk/ops analysts need early signal when customer spend velocity, category mix, or decline rates shift vs baseline. Opaque models and dashboards that recompute KPIs differently from the warehouse create trust gaps.
2. **Approach** — Keep metric definitions in SQL (dbt marts), apply explicit monitoring thresholds in Python, score severity from breach magnitude + multi-signal coincidence, and let a local LLM only narrate evidence it is given.
3. **Delivery** — Seeded generator → DuckDB → dbt → KPI layer → anomaly detection → narration (Ollama or fallback) → Streamlit UI that reads the warehouse. Containerized dashboard for local reproducibility.
4. **Proof** — dbt tests, pytest, numerical reconciliation of dashboard KPIs to DuckDB, and graceful degradation when Ollama is offline.

## What this demonstrates

| Skill | Where it shows up |
|-------|-------------------|
| Analytics engineering | Staging/marts, tests, KPI definitions in SQL |
| Risk / monitoring design | Thresholds, severity, evidence payloads |
| Python data tooling | Generator, DuckDB load, detection, narration |
| LLM boundary discipline | Model explains; rules decide |
| Product sense for analysts | Overview, alert feed, customer drilldown |
| Reproducibility | Make targets, pytest, Docker mounts |

## What this does **not** claim

- Not production banking infrastructure
- Not real-time fraud detection or chargeback prevention
- Not trained ML classifiers or “measured fraud reduction”
- Not a multi-million-row / multi-region deployment
- Not a paid cloud LLM or managed warehouse (by design)

## Interview talking points

**Why rules before ML?**  
Explainability and tunable thresholds matter when analysts must defend an alert. Labeled fraud outcomes were not assumed.

**Why DuckDB + dbt?**  
Laptop-scale warehouse semantics without cloud credentials; dbt keeps the raw → staging → mart contract explicit.

**Why separate narration from detection?**  
LLMs invent numbers under pressure. Every alert stores `metric_value`, `threshold_value`, and `explanation_context` before any prose is written.

**What would you change in a real bank?**  
Swap DuckDB for Snowflake/BigQuery/Redshift via dbt profiles; stream or batch ingest; add case management, RBAC, audit logs; calibrate thresholds on labeled outcomes; keep the evidence-first narration pattern.

**Known soft spot?**  
Category-shift flags are frequent (~31% of customers) on this synthetic seed — treated as a threshold/data-mix issue, not a detection-code defect. See [limitations.md](limitations.md).

## Related docs

- [Demo script](demo_script.md)
- [Resume / LinkedIn bullets](resume_bullets.md)
- [Limitations](limitations.md)
- [Architecture decisions](../DECISIONS.md)
