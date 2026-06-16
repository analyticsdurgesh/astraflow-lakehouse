select
    c.customer_id,
    c.country,
    c.city,
    c.segment,
    count(distinct o.order_id) as orders,
    round(sum(o.total_amount), 2) as lifetime_value,
    max(o.order_ts) as last_order_ts
from {{ source('raw', 'raw_customers') }} c
join {{ ref('stg_orders') }} o using (customer_id)
where o.status in ('paid', 'shipped', 'delivered')
group by 1, 2, 3, 4
