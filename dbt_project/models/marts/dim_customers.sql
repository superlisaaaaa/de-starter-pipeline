-- Customer dimension: who the customer is + their current contract.
select
    c.customer_id,
    c.first_name,
    c.email,
    c.country,
    c.signup_channel,
    k.contract_id,
    k.product,
    k.start_date,
    k.end_date,
    k.is_active
from {{ ref('stg_customers') }} as c
left join {{ ref('stg_contracts') }} as k
    on c.customer_id = k.customer_id
