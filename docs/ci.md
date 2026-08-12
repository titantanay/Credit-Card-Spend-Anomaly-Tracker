# Continuous Integration

GitHub Actions runs the seeded analytics pipeline plus tests on pushes and pull requests.

## Workflow

File: `.github/workflows/ci.yml`

On each run:

1. Create a Python 3.12 venv and install `requirements.txt`
2. `make generate-data` → `ingest` → `dbt-run` → `detect-anomalies` → `narrate-anomalies`
3. `pytest`
4. `make dbt-test`
5. `make verify` — reconciles headline metrics for the default seed-42 portfolio

Ollama is not required in CI. Narration uses the deterministic fallback.

Docker image builds are not part of CI (local reproducibility only; see README).

## Local equivalent

```bash
make install
make generate-data ingest dbt-run detect-anomalies narrate-anomalies
make dbt-test
.venv/bin/pytest -q
make verify
```

Or, after the warehouse already exists:

```bash
make verify
```

`make verify` expects the default generator scale and `RANDOM_SEED=42`. Regenerating with a different seed or volume will fail the numeric checks — update `scripts/verify_acceptance.py` if you intentionally change the baseline.
