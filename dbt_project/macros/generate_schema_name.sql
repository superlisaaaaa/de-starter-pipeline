-- By default dbt names schemas "<target>_<custom>" (e.g. main_silver).
-- This macro keeps the clean names: silver and gold.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
