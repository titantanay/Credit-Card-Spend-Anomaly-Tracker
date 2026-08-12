# KPI Definitions

Primary monitoring metrics are built in `marts.mart_spend_kpis` from
`staging.stg_transactions`. Spend amounts use **approved** transactions only
unless noted. Decline rates use all transaction attempts.

Observation windows are anchored to `as_of_date` = max(`transaction_date`)
in staging.

---

## 1. Spend velocity

**Definition**

```text
spend_velocity = spend_7d / (spend_30d × 7/30)
```

| Input | Window |
|-------|--------|
| `spend_7d` | Approved spend on `[as_of_date - 6 days, as_of_date]` |
| `spend_30d` | Approved spend on `[as_of_date - 29 days, as_of_date]` |

**Interpretation**

- `1.0` — last week matches the 30-day daily pace
- `> 1.0` — spending faster than the recent baseline
- `null` — no approved spend in the 30-day window (velocity undefined)

**Why this formulation**

Comparing a 7-day total to a raw 30-day total would always understate weekly
activity. Scaling the 30-day total to a 7-day equivalent keeps the ratio
dimensionally consistent and easy to explain to risk analysts.

---

## 2. Category shift

**Definition**

For each merchant category, compute approved-spend share in:

| Window | Dates |
|--------|-------|
| Recent | `[as_of_date - 6, as_of_date]` |
| Baseline | `[as_of_date - 36, as_of_date - 7]` (30 days before the recent week) |

```text
category_shift_score = max(|share_recent − share_baseline|) over categories
category_shift_driver = category achieving that maximum
```

**Interpretation**

- `0.0` — category mix unchanged
- `0.35` — at least one category’s share moved by 35 percentage points
- Example: Travel share 10% → 45% yields a contribution of `0.35`

Non-overlapping windows avoid double-counting the recent week inside the
baseline mix.

---

## 3. Decline rate

**Definition**

```text
decline_rate = declined_transactions / total_transactions
```

Reported in `mart_spend_kpis` for 7-day and 30-day lookbacks, and in
`mart_decline_rates` weekly by customer × card type × merchant category.

**Interpretation**

Elevated decline rates can indicate authorization friction, limit pressure, or
unusual attempt patterns. This metric is behavioral, not a confirmed fraud
label.
