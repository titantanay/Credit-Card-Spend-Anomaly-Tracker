"""Smoke tests for project configuration (Phase 1)."""

import config


def test_project_root_exists():
    assert config.PROJECT_ROOT.is_dir()
    assert (config.PROJECT_ROOT / "requirements.txt").is_file()


def test_expected_package_dirs_exist():
    for name in (
        "data_generator",
        "ingestion",
        "anomaly",
        "ai_narration",
        "dashboard",
        "dbt",
        "tests",
        "docs",
    ):
        assert (config.PROJECT_ROOT / name).is_dir()


def test_data_dirs_can_be_created():
    config.ensure_data_dirs()
    assert config.RAW_DATA_DIR.is_dir()
    assert config.PROCESSED_DATA_DIR.is_dir()
    assert config.DATABASE_DIR.is_dir()


def test_default_duckdb_filename():
    assert config.DUCKDB_PATH.name == "spend_monitor.duckdb"
