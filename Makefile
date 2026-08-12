# Developer shortcuts. Requires GNU Make (Git Bash / WSL on Windows).
# Equivalent shell commands are documented in the README as phases land.

.PHONY: help install generate-data ingest

help:
	@echo "Credit Card Spend Anomaly Tracker"
	@echo ""
	@echo "Available:"
	@echo "  make install          Create venv (if needed) and install requirements"
	@echo "  make generate-data    Write synthetic customers/transactions CSVs"
	@echo "  make ingest           Load raw CSVs into DuckDB"
	@echo ""
	@echo "Planned (added in later phases):"
	@echo "  make dbt-run"
	@echo "  make dbt-test"
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
