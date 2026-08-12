with transactions as (
    select * from {{ ref('stg_transactions') }}
),

customers as (
    select
        cast(customer_id as varchar) as customer_id,
        cast(customer_name as varchar) as customer_name,
        trim(cast(card_type as varchar)) as card_type,
        cast(credit_limit as integer) as credit_limit,
        cast(customer_since as date) as customer_since
    from {{ source('raw', 'raw_customers') }}
),

customer_totals as (
    select
        t.customer_id,
        count(*) as transaction_count,
        count(*) filter (where t.transaction_status = 'approved') as approved_count,
        count(*) filter (where t.transaction_status = 'declined') as declined_count,
        coalesce(
            sum(t.transaction_amount) filter (where t.transaction_status = 'approved'),
            0.0
        ) as total_approved_spend,
        coalesce(
            avg(t.transaction_amount) filter (where t.transaction_status = 'approved'),
            0.0
        ) as avg_approved_amount,
        coalesce(
            max(t.transaction_amount) filter (where t.transaction_status = 'approved'),
            0.0
        ) as max_approved_amount,
        count(distinct t.transaction_date) as active_days,
        min(t.transaction_date) as first_transaction_date,
        max(t.transaction_date) as last_transaction_date,
        count(*) filter (where t.transaction_status = 'declined')::double
            / nullif(count(*), 0) as decline_rate
    from transactions as t
    group by 1
),

category_spend as (
    select
        customer_id,
        merchant_category,
        coalesce(
            sum(transaction_amount) filter (where transaction_status = 'approved'),
            0.0
        ) as category_spend
    from transactions
    group by 1, 2
),

category_ranked as (
    select
        customer_id,
        merchant_category as top_category,
        category_spend as top_category_spend,
        row_number() over (
            partition by customer_id
            order by category_spend desc, merchant_category
        ) as category_rank
    from category_spend
),

top_category as (
    select
        customer_id,
        top_category,
        top_category_spend
    from category_ranked
    where category_rank = 1
)

select
    c.customer_id,
    c.customer_name,
    c.card_type,
    c.credit_limit,
    c.customer_since,
    coalesce(ct.transaction_count, 0) as transaction_count,
    coalesce(ct.approved_count, 0) as approved_count,
    coalesce(ct.declined_count, 0) as declined_count,
    coalesce(ct.total_approved_spend, 0.0) as total_approved_spend,
    coalesce(ct.avg_approved_amount, 0.0) as avg_approved_amount,
    coalesce(ct.max_approved_amount, 0.0) as max_approved_amount,
    coalesce(ct.active_days, 0) as active_days,
    ct.first_transaction_date,
    ct.last_transaction_date,
    coalesce(ct.decline_rate, 0.0) as decline_rate,
    tc.top_category,
    coalesce(tc.top_category_spend, 0.0) as top_category_spend,
    case
        when coalesce(ct.total_approved_spend, 0.0) = 0 then 0.0
        else coalesce(tc.top_category_spend, 0.0) / ct.total_approved_spend
    end as top_category_share
from customers as c
left join customer_totals as ct
    on c.customer_id = ct.customer_id
left join top_category as tc
    on c.customer_id = tc.customer_id
