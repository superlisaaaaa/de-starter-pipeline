-- A "singular" test: one specific business rule.
-- Passes when it returns zero rows, fails if any negative kWh reaches gold.
select
    contract_id,
    reading_date,
    kwh
from {{ ref('fct_daily_consumption') }}
where kwh < 0
