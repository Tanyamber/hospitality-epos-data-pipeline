with transactions as (
    select * from {{ ref('stg_transactions') }}
),

visit_sequencing as (
    select
        transaction_id,
        venue_id,
        transaction_ts,
        net_amount,
        -- Generate a pseudo-customer profile based on payment fingerprint to track behaviors
        md5(payment_method || city || venue_type) as customer_surrogate_id,
        
        -- Window function 1: What number visit is this for this specific customer segment?
        row_number() over (
            partition by md5(payment_method || city || venue_type) 
            order by transaction_ts
        ) as customer_visit_number,
        
        -- Window function 2: When was the exact timestamp of their previous visit?
        lag(transaction_ts) over (
            partition by md5(payment_method || city || venue_type) 
            order by transaction_ts
        ) as previous_transaction_ts
    from transactions
)

select
    *,
    -- Calculate exact velocity (days between visits) for advanced predictive forecasting
    datediff('day', previous_transaction_ts, transaction_ts) as days_since_last_visit,
    
    -- Flag customer type for high-level matrix partitioning in Power BI
    case 
        when customer_visit_number = 1 then 'New Guest'
        when datediff('day', previous_transaction_ts, transaction_ts) <= 7 then 'High-Frequency Loyal'
        when datediff('day', previous_transaction_ts, transaction_ts) <= 30 then 'Standard Returning'
        else 'Churned / Reactivated Guest'
    end as customer_loyalty_segment
from visit_sequencing