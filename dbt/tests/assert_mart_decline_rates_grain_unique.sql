-- Composite uniqueness for weekly decline-rate grain.
select
    period_start,
    customer_id,
    card_type,
    merchant_category,
    count(*) as row_count
from {{ ref('mart_decline_rates') }}
group by 1, 2, 3, 4
having count(*) > 1
