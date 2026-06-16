select
    cast(order_ts as date) as order_date,
    count(*) as orders,
    count(distinct customer_id) as active_customers,
    round(sum(total_amount), 2) as revenue,
    round(avg(total_amount), 2) as average_order_value
from {{ ref('stg_orders') }}
where status in ('paid', 'shipped', 'delivered')
group by 1
