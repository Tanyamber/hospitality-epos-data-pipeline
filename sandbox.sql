create or replace view HOSPITALITY_DW.PUBLIC.stg_transactions as (
    select
        -- Primary Key
        transaction_id,
        
        -- Foreign Keys / Dimensions
        venue_id,
        venue_name,
        venue_type,
        city,
        region,
        payment_method,
        
        -- Date/Time fields
        transaction_date,
        transaction_time,
        transaction_ts,
        day_of_week,
        month,
        month_num,
        is_weekend,
        
        -- Core Metrics
        item_name,
        category,
        cast(quantity as int) as quantity,
        cast(unit_price as numeric(8,2)) as unit_price,
        cast(gross_amount as numeric(8,2)) as gross_amount,
        cast(discount_pct as int) as discount_pct,
        cast(discount_amount as numeric(8,2)) as discount_amount,
        cast(net_amount as numeric(8,2)) as net_amount,
        
        -- Audit field
        loaded_at
    from HOSPITALITY_DW.RAW.transactions
);