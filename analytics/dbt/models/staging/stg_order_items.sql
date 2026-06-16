select
    order_item_id,
    order_id,
    sku,
    cast(quantity as integer) as quantity,
    cast(unit_price as double) as unit_price,
    cast(gross_amount as double) as gross_amount,
    cast(discount_amount as double) as discount_amount
from {{ source('raw', 'raw_order_items') }}
