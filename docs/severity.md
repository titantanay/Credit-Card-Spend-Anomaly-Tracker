# Anomaly Severity

Severity labels are **LOW**, **MEDIUM**, and **HIGH**. They are assigned in
`anomaly/severity.py` after detection. Labels are recomputable from stored
`metric_value`, `threshold_value`, and the set of `anomaly_type` values for
the same customer in the detection batch.

---

## 1. Magnitude (per alert)

```text
ratio = metric_value / threshold_value
```

| Ratio | Base severity |
|-------|----------------|
| `< 1.5` | LOW |
| `≥ 1.5` and `< 2.0` | MEDIUM |
| `≥ 2.0` | HIGH |

Defaults live on `SeverityRules.medium_ratio` / `high_ratio`.

## 2. Multi-signal boost (per customer, same run)

Count distinct `anomaly_type` values for the customer:

| Distinct alert types | Effect |
|----------------------|--------|
| 1 | Keep magnitude severity |
| 2 | Bump one level (LOW→MEDIUM, MEDIUM→HIGH, HIGH stays HIGH) |
| 3+ | Force **HIGH** on every alert for that customer |

Rationale: concurrent breaches (e.g. velocity + decline + category shift)
are more operationally urgent than an isolated moderate breach.

---

Severity never invents metric values. It only labels alerts the detector
already created from KPI marts and thresholds.
