-- Typed meter readings, one row per contract per day.
-- Invalid readings (negative kWh) are flagged, not silently deleted,
-- so we can count and report them.
with typed as (
    select
        contract_id,
        cast(reading_date as date) as reading_date,
        cast(kwh as double) as kwh,
        _batch_id
    from {{ source('bronze', 'meter_readings') }}
),

deduplicated as (
    -- if a source re-sends a corrected value for the same day, keep the newest batch
    select
        *,
        row_number() over (
            partition by contract_id, reading_date
            order by _batch_id desc
        ) as version_rank
    from typed
)

select
    contract_id,
    reading_date,
    kwh,
    kwh >= 0 as is_valid
from deduplicated
where version_rank = 1
