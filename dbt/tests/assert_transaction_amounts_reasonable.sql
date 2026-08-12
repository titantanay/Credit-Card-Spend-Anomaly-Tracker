-- Amounts must stay within the synthetic generator bounds.
select
    transaction_id,
    transaction_amount
from {{ ref('stg_transactions') }}
where transaction_amount < 1.0
   or transaction_amount > 8000.0
