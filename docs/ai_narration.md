# AI Narration

Local Ollama (default model `gemma2:2b`, override with `OLLAMA_MODEL`) writes
short analyst-facing prose for alerts that the deterministic detector already
created.

## Rules

1. Detection decides; narration explains.
2. Prompts receive structured evidence only (`metric_value`, `threshold_value`,
   `explanation_context`, etc.).
3. The model must not invent numbers or claim confirmed fraud.
4. If Ollama is unreachable or errors, a deterministic fallback sentence is
   generated from the same evidence so the dashboard still has text
   (`narration_source = fallback`).

## Commands

```bash
make narrate-anomalies
# or
python -m ai_narration.narrator --limit 20
```

Output: `data/processed/anomalies_narrated.csv` and DuckDB table
`anomaly_alert_narrations`.
