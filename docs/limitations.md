# Known Limitations

Documented so demos and interviews stay accurate.

## By design (not defects)

| Topic | Notes |
|-------|--------|
| Synthetic data | No real cardholder data; patterns are seeded and injected for detectability. |
| Batch scale | ~50k transactions / 90 days / 1,000 customers — laptop prototype, not a streaming platform. |
| Rule-based detection | Thresholds are explicit business rules, not supervised fraud models. |
| Optional LLM | Ollama is not required for detection or dashboard startup; fallback narration is used when offline. |
| Local Docker | Reproducibility packaging only — not a production deployment, HA, or multi-tenant bank stack. |

## Calibration backlog

### Category-shift flag rate (~31%)

On the acceptance seed, category-shift alerts fire for a large share of customers. This was classified as a **LOW synthetic-data / threshold calibration** issue, not a logic defect in the detector.

- **Do not treat** the high flag rate as proof the rule is “working better.”
- **Do not silently retune** thresholds without documenting the change and re-reconciling.
- Sensible follow-ups: tighten the shift threshold, require a minimum recent spend/txn count, or adjust synthetic category-mix noise — then re-run detection and dashboard reconciliation.

### Other soft edges

- Floating-point display in the UI is rounded for presentation; reconciliation uses warehouse numeric values.
- Severity is heuristic (magnitude + multi-signal boost), not a calibrated probability of loss.
- Large-transaction alerts use a fixed dollar threshold; no customer-specific ticket baselines yet.
- Dashboard reads analytical outputs; it does not manage cases, assignments, or audit workflows.

## Explicit non-goals (current repo)

- Real-time authorization scoring
- Card network integrations
- PII-safe production controls / SSO / RBAC
- Claiming measured fraud loss reduction
- Bundling GPU/Ollama inside the dashboard image

## If extending later

Prefer changes that preserve: one KPI definition path (dbt), evidence-first alerts, and LLM-as-narrator. See [DECISIONS.md](../DECISIONS.md) and [portfolio.md](portfolio.md).
