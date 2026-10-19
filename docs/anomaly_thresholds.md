# Monitoring Thresholds

Business rules used to interpret KPI mart outputs. Stored in
`kpi/thresholds.py` as `MonitoringThresholds`. The analytics layer decides
what is elevated; `anomaly/detector.py` emits alerts from these rules.
The LLM never sets or overrides these values.

---

## Spend velocity — `spend_velocity_min = 2.0`

Flag when:

```text
spend_7d / (spend_30d × 7/30) ≥ 2.0
```

**Reasoning:** A value of `1.0` means the last week matches the 30-day pace.
`2.0` means the customer spent about twice that pace — an extra week of typical
spend inside seven days. That is unusual enough for review without treating
every modest above-baseline week as an alert.

## Category shift — `category_shift_min = 0.35`

Flag when the largest absolute category-share change (recent 7d vs prior 30d
baseline) is at least 0.35.

**Reasoning:** Matches the documented example (Travel 10% → 45%). Smaller moves
are common week to week; a 35-point share swing is a clear mix break.

## Decline rate — `decline_rate_7d_min = 0.15`

Flag when the 7-day decline rate is at least 15%.

**Reasoning:** The synthetic portfolio’s overall decline rate is about 6%.
Fifteen percent is roughly 2.5× that baseline. Combined with
`min_txn_count_7d`, a single decline in a very thin week does not always fire.

## Large transaction — `large_transaction_amount_min = 1500`

Flag Approved tickets at or above $1,500 (evaluated from customer max ticket in
the spend mart / transaction grain in detection).

**Reasoning:** Above routine grocery/dining amounts and inside elevated
travel/electronics territory for this synthetic generator (amounts clipped at
$8,000).

## Activity floor — `min_txn_count_7d = 3`

Ratio KPIs (velocity, category shift, decline rate) only count as elevated when
the customer has at least three transactions in the recent 7-day window.

**Reasoning:** Sparse weeks make percentages unstable.

---

Retune these constants when connecting real card data. Keep a single source of
truth in `kpi/thresholds.py` — do not scatter literals across detectors or the
dashboard.
