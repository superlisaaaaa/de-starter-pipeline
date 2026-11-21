-- One row per customer: the LATEST version.
-- Bronze keeps every version we ever received (history);
-- silver keeps the current truth.
with ranked as (
    select
        customer_id,
        first_name,
        lower(email) as email,
        upper(country) as country,
        signup_channel,
        cast(updated_at as timestamp) as updated_at,
        row_number() over (
            partition by customer_id
            order by cast(updated_at as timestamp) desc
        ) as version_rank
    from {{ source('bronze', 'customers') }}
)

select
    customer_id,
    first_name,
    email,
    country,
    signup_channel,
    updated_at
from ranked
where version_rank = 1
