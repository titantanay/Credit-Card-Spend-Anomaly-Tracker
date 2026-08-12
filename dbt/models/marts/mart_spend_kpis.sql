/*
  Customer monitoring KPIs as of the latest transaction date in staging.

  Spend velocity:
    spend_7d / (spend_30d * 7/30)
    Values near 1.0 mean the last week matches the 30-day daily pace.
    Values materially above 1.0 indicate accelerated spend.

  Category shift:
    max(|share_7d - share_baseline|) across merchant categories.
    Baseline window is the 30 days immediately before the recent 7-day window.

  Decline rate:
    declined_txns / total_txns for the 7-day and 30-day lookbacks.
*/

with transactions as (
    select * from {{ ref('stg_transactions') }}
),

bounds as (
    select max(transaction_date) as as_of_date
    from transactions
),

windows as (
    select
        as_of_date,
        (as_of_date - interval 6 day)::date as recent_start,
        (as_of_date - interval 36 day)::date as baseline_start,
        (as_of_date - interval 7 day)::date as baseline_end,
        (as_of_date - interval 29 day)::date as lookback_30_start
    from bounds
),

customer_spine as (
    select distinct customer_id, card_type
    from transactions
),

spend_windows as (
    select
        t.customer_id,
        coalesce(
            sum(t.transaction_amount) filter (
                where t.transaction_status = 'Approved'
                  and t.transaction_date between w.recent_start and w.as_of_date
            ),
            0.0
        ) as spend_7d,
        coalesce(
            sum(t.transaction_amount) filter (
                where t.transaction_status = 'Approved'
                  and t.transaction_date between w.lookback_30_start and w.as_of_date
            ),
            0.0
        ) as spend_30d,
        count(*) filter (
            where t.transaction_date between w.recent_start and w.as_of_date
        ) as txn_count_7d,
        count(*) filter (
            where t.transaction_date between w.lookback_30_start and w.as_of_date
        ) as txn_count_30d,
        count(*) filter (
            where t.transaction_status = 'Declined'
              and t.transaction_date between w.recent_start and w.as_of_date
        ) as declined_count_7d,
        count(*) filter (
            where t.transaction_status = 'Declined'
              and t.transaction_date between w.lookback_30_start and w.as_of_date
        ) as declined_count_30d
    from transactions as t
    cross join windows as w
    group by 1
),

recent_category as (
    select
        t.customer_id,
        t.merchant_category,
        coalesce(
            sum(t.transaction_amount) filter (where t.transaction_status = 'Approved'),
            0.0
        ) as spend
    from transactions as t
    cross join windows as w
    where t.transaction_date between w.recent_start and w.as_of_date
    group by 1, 2
),

baseline_category as (
    select
        t.customer_id,
        t.merchant_category,
        coalesce(
            sum(t.transaction_amount) filter (where t.transaction_status = 'Approved'),
            0.0
        ) as spend
    from transactions as t
    cross join windows as w
    where t.transaction_date between w.baseline_start and w.baseline_end
    group by 1, 2
),

category_union as (
    select customer_id, merchant_category from recent_category
    union
    select customer_id, merchant_category from baseline_category
),

category_shares as (
    select
        u.customer_id,
        u.merchant_category,
        coalesce(r.spend, 0.0) as spend_7d,
        coalesce(b.spend, 0.0) as spend_baseline,
        coalesce(r.spend, 0.0)
            / nullif(sum(coalesce(r.spend, 0.0)) over (partition by u.customer_id), 0)
            as share_7d,
        coalesce(b.spend, 0.0)
            / nullif(sum(coalesce(b.spend, 0.0)) over (partition by u.customer_id), 0)
            as share_baseline
    from category_union as u
    left join recent_category as r
        on u.customer_id = r.customer_id
       and u.merchant_category = r.merchant_category
    left join baseline_category as b
        on u.customer_id = b.customer_id
       and u.merchant_category = b.merchant_category
),

category_shift as (
    select
        customer_id,
        max(abs(coalesce(share_7d, 0.0) - coalesce(share_baseline, 0.0)))
            as category_shift_score,
        arg_max(
            merchant_category,
            abs(coalesce(share_7d, 0.0) - coalesce(share_baseline, 0.0))
        ) as category_shift_driver
    from category_shares
    group by 1
)

select
    w.as_of_date,
    s.customer_id,
    s.card_type,
    sw.spend_7d,
    sw.spend_30d,
    case
        when sw.spend_30d <= 0 then null
        else sw.spend_7d / (sw.spend_30d * 7.0 / 30.0)
    end as spend_velocity,
    coalesce(cs.category_shift_score, 0.0) as category_shift_score,
    cs.category_shift_driver,
    sw.txn_count_7d,
    sw.txn_count_30d,
    sw.declined_count_7d,
    sw.declined_count_30d,
    sw.declined_count_7d::double / nullif(sw.txn_count_7d, 0) as decline_rate_7d,
    sw.declined_count_30d::double / nullif(sw.txn_count_30d, 0) as decline_rate_30d
from customer_spine as s
cross join windows as w
inner join spend_windows as sw
    on s.customer_id = sw.customer_id
left join category_shift as cs
    on s.customer_id = cs.customer_id
