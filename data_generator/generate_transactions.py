"""Generate synthetic credit-card customers and transactions.

Produces deterministic CSV files under data/raw/ for local analytics.
Behavioral profiles inject patterned spend so rule-based anomaly detection
has realistic signal — this is synthetic data, not production card activity.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import config as app_config
from data_generator import config as gen_config

CUSTOMER_COLUMNS = [
    "customer_id",
    "customer_name",
    "card_type",
    "credit_limit",
    "customer_since",
]

TRANSACTION_COLUMNS = [
    "transaction_id",
    "customer_id",
    "transaction_timestamp",
    "merchant_category",
    "transaction_amount",
    "transaction_status",
    "card_type",
]

FIRST_NAMES = (
    "Alex", "Jordan", "Sam", "Taylor", "Casey", "Morgan", "Riley", "Avery",
    "Quinn", "Jamie", "Cameron", "Drew", "Parker", "Reese", "Skyler", "Blake",
    "Harper", "Rowan", "Finley", "Hayden",
)
LAST_NAMES = (
    "Nguyen", "Patel", "Garcia", "Kim", "Brown", "Lopez", "Singh", "Chen",
    "Wilson", "Martinez", "Ali", "Thompson", "Rivera", "Brooks", "Foster",
    "Reed", "Bennett", "Gray", "Hayes", "Price",
)


def _credit_limit_for_card(card_type: str, rng: np.random.Generator) -> int:
    ranges = {
        "Classic": (1_500, 5_000),
        "Gold": (5_000, 15_000),
        "Platinum": (12_000, 30_000),
    }
    low, high = ranges[card_type]
    return int(rng.integers(low, high + 1))


def _assign_profiles(n: int, rng: np.random.Generator) -> list[set[str]]:
    profiles = [set() for _ in range(n)]
    indices = np.arange(n)
    for name, rate in gen_config.PROFILE_RATES.items():
        k = max(1, int(round(n * rate)))
        chosen = rng.choice(indices, size=k, replace=False)
        for i in chosen:
            profiles[int(i)].add(name)
    return profiles


def _category_weights(base_prefs: np.ndarray, profiles: set[str]) -> np.ndarray:
    weights = base_prefs.copy()
    categories = list(gen_config.MERCHANT_CATEGORIES)
    if "travel_heavy" in profiles:
        travel_idx = categories.index("Travel")
        weights[travel_idx] *= 4.0
    weights = weights / weights.sum()
    return weights


def generate_customers(rng: np.random.Generator) -> pd.DataFrame:
    n = gen_config.N_CUSTOMERS
    history_start = gen_config.HISTORY_END_DATE - timedelta(days=gen_config.HISTORY_DAYS)

    rows = []
    for i in range(n):
        customer_id = f"C{i + 1:04d}"
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        card_type = str(rng.choice(gen_config.CARD_TYPES, p=[0.55, 0.30, 0.15]))
        credit_limit = _credit_limit_for_card(card_type, rng)
        # Tenure starts before the observation window
        tenure_days = int(rng.integers(180, 3600))
        customer_since = history_start - timedelta(days=tenure_days)
        rows.append(
            {
                "customer_id": customer_id,
                "customer_name": name,
                "card_type": card_type,
                "credit_limit": credit_limit,
                "customer_since": customer_since.isoformat(),
            }
        )
    return pd.DataFrame(rows, columns=CUSTOMER_COLUMNS)


def _draw_amount(
    category: str,
    profiles: set[str],
    spend_scale: float,
    rng: np.random.Generator,
) -> float:
    mean, std = gen_config.CATEGORY_AMOUNT_PARAMS[category]
    amount = float(rng.normal(mean * spend_scale, std * spend_scale))
    if "high_spender" in profiles:
        amount *= float(rng.uniform(1.4, 2.0))
    if "large_ticket" in profiles and rng.random() < 0.08:
        amount *= float(rng.uniform(3.0, 6.0))
    amount = abs(amount)
    return float(
        np.clip(round(amount, 2), gen_config.MIN_AMOUNT, gen_config.MAX_AMOUNT)
    )


def _decline_probability(profiles: set[str], amount: float, credit_limit: int) -> float:
    base = 0.035
    if "decline_prone" in profiles:
        base = 0.18
    # Larger tickets relative to limit decline more often
    utilization_pressure = min(0.12, amount / max(credit_limit, 1) * 0.5)
    return min(0.55, base + utilization_pressure)


def generate_transactions(
    customers: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    n_customers = len(customers)
    profiles = _assign_profiles(n_customers, rng)

    # Per-customer activity level and category preference
    tx_share = rng.dirichlet(np.ones(n_customers) * 2.0)
    # Ensure we land near the target count
    counts = rng.multinomial(gen_config.N_TRANSACTIONS, tx_share)

    history_end = datetime.combine(gen_config.HISTORY_END_DATE, datetime.min.time())
    history_start = history_end - timedelta(days=gen_config.HISTORY_DAYS - 1)

    categories = list(gen_config.MERCHANT_CATEGORIES)
    rows: list[dict] = []

    for idx, customer in customers.iterrows():
        n_tx = int(counts[idx])
        if n_tx == 0:
            continue

        cust_profiles = profiles[idx]
        spend_scale = float(rng.uniform(0.6, 1.1))
        if "high_spender" in cust_profiles:
            spend_scale *= float(rng.uniform(1.5, 2.2))

        base_prefs = rng.dirichlet(np.ones(len(categories)))
        weights = _category_weights(base_prefs, cust_profiles)

        # Default: uniform over window; velocity_spike customers load the last 7 days
        if "velocity_spike" in cust_profiles:
            early = int(n_tx * 0.55)
            late = n_tx - early
            early_offsets = rng.integers(0, gen_config.HISTORY_DAYS - 7, size=early)
            late_offsets = rng.integers(
                gen_config.HISTORY_DAYS - 7, gen_config.HISTORY_DAYS, size=late
            )
            day_offsets = np.concatenate([early_offsets, late_offsets])
            rng.shuffle(day_offsets)
        else:
            day_offsets = rng.integers(0, gen_config.HISTORY_DAYS, size=n_tx)

        credit_limit = int(customer["credit_limit"])
        card_type = customer["card_type"]
        customer_id = customer["customer_id"]

        for day_offset in day_offsets:
            category = str(rng.choice(categories, p=weights))
            amount = _draw_amount(category, cust_profiles, spend_scale, rng)
            decline_p = _decline_probability(cust_profiles, amount, credit_limit)
            status = "declined" if rng.random() < decline_p else "approved"

            hour = int(rng.integers(6, 23))
            minute = int(rng.integers(0, 60))
            second = int(rng.integers(0, 60))
            ts = history_start + timedelta(
                days=int(day_offset), hours=hour, minutes=minute, seconds=second
            )

            rows.append(
                {
                    "transaction_id": "",
                    "customer_id": customer_id,
                    "transaction_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "merchant_category": category,
                    "transaction_amount": amount,
                    "transaction_status": status,
                    "card_type": card_type,
                }
            )

    transactions = (
        pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)
        .sort_values("transaction_timestamp")
        .reset_index(drop=True)
    )
    transactions["transaction_id"] = [
        f"T{i + 1:08d}" for i in range(len(transactions))
    ]
    return transactions


def write_outputs(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    customers_path: Path,
    transactions_path: Path,
) -> None:
    app_config.ensure_data_dirs()
    customers.to_csv(customers_path, index=False)
    transactions.to_csv(transactions_path, index=False)


def run(
    customers_path: Path | None = None,
    transactions_path: Path | None = None,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed = gen_config.RANDOM_SEED if seed is None else seed
    rng = np.random.default_rng(seed)

    customers = generate_customers(rng)
    transactions = generate_transactions(customers, rng)

    customers_path = customers_path or app_config.CUSTOMERS_CSV
    transactions_path = transactions_path or app_config.RAW_TRANSACTIONS_CSV
    write_outputs(customers, transactions, customers_path, transactions_path)

    return customers, transactions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic credit-card customers and transactions."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=gen_config.RANDOM_SEED,
        help=f"RNG seed (default: {gen_config.RANDOM_SEED})",
    )
    parser.add_argument(
        "--customers-out",
        type=Path,
        default=app_config.CUSTOMERS_CSV,
    )
    parser.add_argument(
        "--transactions-out",
        type=Path,
        default=app_config.RAW_TRANSACTIONS_CSV,
    )
    args = parser.parse_args()

    customers, transactions = run(
        customers_path=args.customers_out,
        transactions_path=args.transactions_out,
        seed=args.seed,
    )

    print(f"Wrote {len(customers):,} customers → {args.customers_out}")
    print(f"Wrote {len(transactions):,} transactions → {args.transactions_out}")
    print(
        f"Window: {gen_config.HISTORY_DAYS} days ending {gen_config.HISTORY_END_DATE} "
        f"(seed={args.seed})"
    )


if __name__ == "__main__":
    main()
