# Developer shortcuts. Requires GNU Make (Git Bash / WSL on Windows).
# Run targets from the repository root.

.PHONY: help install generate-data ingest dbt-clean dbt-debug dbt-run dbt-test

DBT := .venv/bin/dbt
export DUCKDB_PATH ?= $(CURDIR)/database/spend_monitor.duckdb

help:
	@echo "Credit Card Spend Anomaly Tracker"
	@echo ""
	@echo "Available:"
	@echo "  make install          Create venv (if needed) and install requirements"
	@echo "  make generate-data    Write synthetic customers/transactions CSVs"
	@echo "  make ingest           Load raw CSVs into DuckDB"
	@echo "  make dbt-clean        Remove dbt target/dbt_packages artifacts"
	@echo "  make dbt-debug        Check dbt ↔ DuckDB connectivity"
	@echo "  make dbt-run          Build dbt models"
	@echo "  make dbt-test         Run dbt data tests"
	@echo ""
	@echo "Planned (added in later phases):"
	@echo "  make detect-anomalies"
	@echo "  make dashboard"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

generate-data:
	.venv/bin/python -m data_generator.generate_transactions

ingest:
	.venv/bin/python -m ingestion.load_to_duckdb

# dbt clean must run with cwd=dbt; --project-dir from repo root rejects clean paths.
dbt-clean:
	cd dbt && ../$(DBT) clean --profiles-dir .

dbt-debug:
	$(DBT) debug --project-dir dbt --profiles-dir dbt

dbt-run:
	$(DBT) run --project-dir dbt --profiles-dir dbt

dbt-test:
	$(DBT) test --project-dir dbt --profiles-dir dbt
