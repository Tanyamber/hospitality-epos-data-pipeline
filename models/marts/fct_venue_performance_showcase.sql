with staging_data as (
    select * from {{ ref('stg_transactions') }}
)

select
    -- Dimensions
    venue_id,
    venue_name,
    venue_type,
    city,
    region,
    category,
    item_name,
    day_of_week,
    month,
    
    -- Aggregated Showcase Metrics
    sum(quantity) as total_units_sold,
    count(distinct transaction_id) as total_transactions,
    sum(gross_amount) as total_gross_revenue,
    sum(discount_amount) as total_discounts_given,
    sum(net_amount) as total_net_revenue,
    avg(unit_price) as average_item_price,
    
    -- Timestamp
    max(loaded_at) as last_pipeline_update
from staging_data
group by 
    venue_id, venue_name, venue_type, city, region, 
    category, item_name, day_of_week, month