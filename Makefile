# Developer shortcuts. Requires GNU Make (Git Bash / WSL on Windows).
# Run targets from the repository root.

.PHONY: help install generate-data ingest dbt-clean dbt-debug dbt-run dbt-test \
	kpi-summary detect-anomalies narrate-anomalies dashboard \
	docker-build docker-up docker-down pipeline verify

PYTHON := .venv/bin/python
DBT := .venv/bin/dbt
export DUCKDB_PATH ?= $(CURDIR)/database/spend_monitor.duckdb

help:
	@echo "Credit Card Spend Anomaly Tracker"
	@echo ""
	@echo "Available:"
	@echo "  make install            Create venv (if needed) and install requirements"
	@echo "  make generate-data      Write synthetic customers/transactions CSVs"
	@echo "  make ingest             Load raw CSVs into DuckDB"
	@echo "  make dbt-clean          Remove dbt target/dbt_packages artifacts"
	@echo "  make dbt-debug          Check dbt ↔ DuckDB connectivity"
	@echo "  make dbt-run            Build dbt models"
	@echo "  make dbt-test           Run dbt data tests"
	@echo "  make kpi-summary        Summarize KPI marts vs monitoring thresholds"
	@echo "  make detect-anomalies   Run rule-based anomaly detection"
	@echo "  make narrate-anomalies  Narrate alerts via Ollama (fallback if offline)"
	@echo "  make dashboard          Launch Streamlit monitoring UI"
	@echo "  make docker-build       Build local dashboard image"
	@echo "  make docker-up          Start dashboard container (mounts database/ + data/)"
	@echo "  make docker-down        Stop dashboard container"
	@echo "  make pipeline           generate → ingest → dbt → detect → narrate"
	@echo "  make verify             Reconcile seed-42 acceptance metrics"

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

generate-data:
	$(PYTHON) -m data_generator.generate_transactions

ingest:
	$(PYTHON) -m ingestion.load_to_duckdb

# dbt clean must run with cwd=dbt; --project-dir from repo root rejects clean paths.
dbt-clean:
	cd dbt && ../$(DBT) clean --profiles-dir .

dbt-debug:
	$(DBT) debug --project-dir dbt --profiles-dir dbt

dbt-run:
	$(DBT) run --project-dir dbt --profiles-dir dbt

dbt-test:
	$(DBT) test --project-dir dbt --profiles-dir dbt

kpi-summary:
	$(PYTHON) -m kpi.summarize

detect-anomalies:
	$(PYTHON) -m anomaly.detector

narrate-anomalies:
	$(PYTHON) -m ai_narration.narrator

dashboard:
	.venv/bin/streamlit run dashboard/app.py --server.port=8501

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

pipeline: generate-data ingest dbt-run detect-anomalies narrate-anomalies

verify:
	$(PYTHON) scripts/verify_acceptance.py
