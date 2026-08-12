with source as (
    select * from {{ source('raw', 'raw_transactions') }}
),

cleaned as (
    select
        cast(transaction_id as varchar) as transaction_id,
        cast(customer_id as varchar) as customer_id,
        cast(transaction_timestamp as timestamp) as transaction_timestamp,
        cast(transaction_timestamp as date) as transaction_date,
        date_trunc('week', cast(transaction_timestamp as timestamp))::date
            as transaction_week_start,
        extract(year from cast(transaction_timestamp as timestamp))::integer
            as transaction_year,
        extract(month from cast(transaction_timestamp as timestamp))::integer
            as transaction_month,
        trim(cast(merchant_category as varchar)) as merchant_category,
        cast(transaction_amount as double) as transaction_amount,
        lower(trim(cast(transaction_status as varchar))) as transaction_status,
        trim(cast(card_type as varchar)) as card_type
    from source
)

select * from cleaned
