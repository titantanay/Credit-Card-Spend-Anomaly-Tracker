"""Synthetic data generation parameters."""

from __future__ import annotations

from datetime import date

# Reproducibility
RANDOM_SEED = 42

# Scale targets (approximate; exact counts depend on sampling)
N_CUSTOMERS = 1_000
N_TRANSACTIONS = 50_000
HISTORY_DAYS = 90

# Fixed end date so regenerations stay aligned with docs/examples
HISTORY_END_DATE = date(2025, 12, 31)

CARD_TYPES = ("Classic", "Gold", "Platinum")

MERCHANT_CATEGORIES = (
    "Groceries",
    "Travel",
    "Dining",
    "Fuel",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Electronics",
    "Fashion",
)

TRANSACTION_STATUSES = ("Approved", "Declined")

# Typical ticket sizes by category (mean, std) in USD — used as base draws
CATEGORY_AMOUNT_PARAMS: dict[str, tuple[float, float]] = {
    "Groceries": (65.0, 25.0),
    "Travel": (420.0, 280.0),
    "Dining": (55.0, 30.0),
    "Fuel": (45.0, 18.0),
    "Entertainment": (80.0, 50.0),
    "Utilities": (120.0, 40.0),
    "Healthcare": (150.0, 90.0),
    "Electronics": (280.0, 200.0),
    "Fashion": (95.0, 70.0),
}

# Share of customers assigned special behavioral profiles
PROFILE_RATES = {
    "high_spender": 0.12,
    "travel_heavy": 0.08,
    "decline_prone": 0.06,
    "velocity_spike": 0.05,
    "large_ticket": 0.07,
}

MIN_AMOUNT = 1.0
MAX_AMOUNT = 8_000.0
