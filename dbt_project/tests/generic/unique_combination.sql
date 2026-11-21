-- A reusable ("generic") test: the combination of these columns must be unique.
-- A test passes when its query returns ZERO rows.
{% test unique_combination(model, columns) %}
select
    {{ columns | join(', ') }},
    count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
