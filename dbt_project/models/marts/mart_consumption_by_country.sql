-- Business-ready summary: what a dashboard would read.
select
    c.country,
    c.signup_channel,
    count(distinct f.customer_id) as customers,
    round(sum(f.kwh), 1) as total_kwh,
    round(avg(f.kwh), 2) as avg_daily_kwh_per_customer
from {{ ref('fct_daily_consumption') }} as f
inner join {{ ref('dim_customers') }} as c
    on f.customer_id = c.customer_id
group by c.country, c.signup_channel
