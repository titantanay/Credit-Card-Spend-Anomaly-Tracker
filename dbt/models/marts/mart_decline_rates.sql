with transactions as (
    select * from {{ ref('stg_transactions') }}
),

weekly as (
    select
        transaction_week_start as period_start,
        'week' as period_type,
        customer_id,
        card_type,
        merchant_category,
        count(*) as transaction_count,
        count(*) filter (where transaction_status = 'Declined') as declined_count,
        count(*) filter (where transaction_status = 'Approved') as approved_count,
        coalesce(
            sum(transaction_amount) filter (where transaction_status = 'Approved'),
            0.0
        ) as approved_spend,
        count(*) filter (where transaction_status = 'Declined')::double
            / nullif(count(*), 0) as decline_rate
    from transactions
    group by 1, 2, 3, 4, 5
)

select * from weekly
