select
    order_id,
    customer_id,
    cast(order_ts as timestamp) as order_ts,
    channel,
    status,
    currency,
    cast(subtotal as double) as subtotal,
    cast(discount as double) as discount,
    cast(shipping_fee as double) as shipping_fee,
    cast(tax as double) as tax,
    cast(total_amount as double) as total_amount,
    campaign_id,
    device_type
from {{ source('raw', 'raw_orders') }}
where status in ('paid', 'shipped', 'delivered', 'returned')
