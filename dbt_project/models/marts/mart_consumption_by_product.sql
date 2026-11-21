-- kWh by product type: which contracts use the most energy?
select
    c.product,
    count(distinct f.contract_id) as contracts,
    round(sum(f.kwh), 1) as total_kwh
from {{ ref('fct_daily_consumption') }} as f
inner join {{ ref('dim_customers') }} as c
    on f.contract_id = c.contract_id
group by c.product
