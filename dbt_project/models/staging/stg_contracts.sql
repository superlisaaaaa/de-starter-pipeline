-- Typed contracts with an easy-to-use status flag.
select
    contract_id,
    customer_id,
    product,
    cast(start_date as date) as start_date,
    cast(end_date as date) as end_date,
    end_date is null as is_active
from {{ source('bronze', 'contracts') }}
