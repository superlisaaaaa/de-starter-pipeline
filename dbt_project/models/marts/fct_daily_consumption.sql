-- Daily consumption fact table, built INCREMENTALLY.
-- First run: builds the whole table.
-- Later runs: only processes days newer than what the table already has
-- (minus a 3-day look-back for late corrections), then merges on the unique key.
-- This is how pipelines stay fast when data grows to millions of rows.
{{
    config(
        materialized='incremental',
        unique_key=['contract_id', 'reading_date'],
        incremental_strategy='delete+insert'
    )
}}

select
    r.contract_id,
    k.customer_id,
    r.reading_date,
    r.kwh
from {{ ref('stg_meter_readings') }} as r
inner join {{ ref('stg_contracts') }} as k
    on r.contract_id = k.contract_id
where
    r.is_valid

    {% if is_incremental() %}
        and r.reading_date >= (
            select max(t.reading_date) - interval 3 day
            from {{ this }} as t
        )
    {% endif %}
