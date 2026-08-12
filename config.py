"""Central paths and runtime settings for the spend anomaly tracker."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DATABASE_DIR = PROJECT_ROOT / "database"

RAW_TRANSACTIONS_CSV = RAW_DATA_DIR / "transactions.csv"
CUSTOMERS_CSV = RAW_DATA_DIR / "customers.csv"
ANOMALIES_CSV = PROCESSED_DATA_DIR / "anomalies.csv"
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt"

DUCKDB_PATH = Path(
    os.getenv("DUCKDB_PATH", str(DATABASE_DIR / "spend_monitor.duckdb"))
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")


def ensure_data_dirs() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
