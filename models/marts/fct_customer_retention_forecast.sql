with customer_history as (
    select * from {{ ref('int_customer_visit_history') }}
)

select
    date_trunc('month', transaction_ts) as forecast_month,
    venue_type,
    customer_loyalty_segment,
    count(distinct transaction_id) as total_bookings,
    sum(net_amount) as realized_revenue,
    avg(days_since_last_visit) as average_days_between_visit,
    
    -- Creating a baseline trajectory metric for Power BI to calculate future revenue trends
    round(avg(net_amount), 2) as customer_lifetime_value_increment
from customer_history
group by 1, 2, 3
order by 1 desc, 4 desc