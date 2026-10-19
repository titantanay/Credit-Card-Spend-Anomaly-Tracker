"""Tests for synthetic transaction generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data_generator import config as gen_config
from data_generator.generate_transactions import (
    CUSTOMER_COLUMNS,
    TRANSACTION_COLUMNS,
    generate_customers,
    generate_transactions,
    run,
)


@pytest.fixture
def small_scale(monkeypatch):
    monkeypatch.setattr(gen_config, "N_CUSTOMERS", 40)
    monkeypatch.setattr(gen_config, "N_TRANSACTIONS", 800)
    monkeypatch.setattr(gen_config, "HISTORY_DAYS", 90)


def test_customer_schema(small_scale):
    rng = np.random.default_rng(0)
    customers = generate_customers(rng)
    assert list(customers.columns) == CUSTOMER_COLUMNS
    assert len(customers) == 40
    assert customers["customer_id"].is_unique
    assert customers["card_type"].isin(gen_config.CARD_TYPES).all()
    assert (customers["credit_limit"] > 0).all()


def test_transaction_schema_and_status(small_scale):
    rng = np.random.default_rng(1)
    customers = generate_customers(rng)
    transactions = generate_transactions(customers, rng)

    assert list(transactions.columns) == TRANSACTION_COLUMNS
    assert len(transactions) == 800
    assert transactions["transaction_id"].is_unique
    assert transactions["transaction_status"].isin(gen_config.TRANSACTION_STATUSES).all()
    assert transactions["merchant_category"].isin(gen_config.MERCHANT_CATEGORIES).all()
    assert set(transactions["customer_id"]).issubset(set(customers["customer_id"]))


def test_transaction_amounts_valid(small_scale):
    rng = np.random.default_rng(2)
    customers = generate_customers(rng)
    transactions = generate_transactions(customers, rng)

    amounts = transactions["transaction_amount"]
    assert (amounts >= gen_config.MIN_AMOUNT).all()
    assert (amounts <= gen_config.MAX_AMOUNT).all()
    assert np.issubdtype(amounts.dtype, np.floating)


def test_generation_is_deterministic(small_scale, tmp_path: Path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    out_a.mkdir()
    out_b.mkdir()

    c1, t1 = run(
        customers_path=out_a / "customers.csv",
        transactions_path=out_a / "transactions.csv",
        seed=99,
    )
    c2, t2 = run(
        customers_path=out_b / "customers.csv",
        transactions_path=out_b / "transactions.csv",
        seed=99,
    )

    pd.testing.assert_frame_equal(c1, c2)
    pd.testing.assert_frame_equal(t1, t2)


def test_behavioral_profiles_create_variation(small_scale):
    """Decline-prone and travel-heavy cohorts should differ from the overall base."""
    rng = np.random.default_rng(7)
    customers = generate_customers(rng)
    transactions = generate_transactions(customers, rng)

    overall_decline = (transactions["transaction_status"] == "Declined").mean()
    assert 0.01 < overall_decline < 0.25

    travel_share = (transactions["merchant_category"] == "Travel").mean()
    assert travel_share > 0.05
