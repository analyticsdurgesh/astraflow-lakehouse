select
    i.sku,
    p.category,
    p.brand,
    sum(i.quantity) as units_sold,
    round(sum(i.gross_amount - i.discount_amount), 2) as net_item_revenue,
    round(avg(cast(p.margin_percent as double)), 3) as avg_margin_percent
from {{ ref('stg_order_items') }} i
join {{ source('raw', 'raw_products') }} p using (sku)
join {{ ref('stg_orders') }} o using (order_id)
where o.status in ('paid', 'shipped', 'delivered')
group by 1, 2, 3
