from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def sql_path(path: Path) -> str:
    return str(path).replace("'", "''")


def load_sql(con: Any, table: str, path: Path) -> None:
    escaped = sql_path(path)
    if path.suffix == ".csv":
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto('{escaped}', header=true)")
    else:
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_json_auto('{escaped}', format='newline_delimited')"
        )


def build_warehouse(data_dir: Path, db_path: Path, export_dir: Path | None = None) -> dict[str, Any]:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("DuckDB is required. Install with: pip install -e '.[dev]'") from exc

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))

    load_sql(con, "raw_customers", data_dir / "customers.csv")
    load_sql(con, "raw_products", data_dir / "products.csv")
    load_sql(con, "raw_orders", data_dir / "orders.jsonl")
    load_sql(con, "raw_order_items", data_dir / "order_items.jsonl")
    load_sql(con, "raw_payments", data_dir / "payments.jsonl")
    load_sql(con, "raw_shipments", data_dir / "shipments.jsonl")
    load_sql(con, "raw_clickstream_events", data_dir / "clickstream_events.jsonl")
    load_sql(con, "raw_inventory_snapshots", data_dir / "inventory_snapshots.jsonl")
    load_sql(con, "raw_support_tickets", data_dir / "support_tickets.jsonl")

    con.execute(
        """
        CREATE OR REPLACE VIEW silver_orders AS
        SELECT
            order_id,
            customer_id,
            CAST(order_ts AS TIMESTAMP) AS order_ts,
            channel,
            status,
            currency,
            CAST(subtotal AS DOUBLE) AS subtotal,
            CAST(discount AS DOUBLE) AS discount,
            CAST(shipping_fee AS DOUBLE) AS shipping_fee,
            CAST(tax AS DOUBLE) AS tax,
            CAST(total_amount AS DOUBLE) AS total_amount,
            campaign_id,
            device_type
        FROM raw_orders
        WHERE status IN ('paid', 'shipped', 'delivered', 'returned')
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW silver_order_items AS
        SELECT
            order_item_id,
            order_id,
            sku,
            CAST(quantity AS INTEGER) AS quantity,
            CAST(unit_price AS DOUBLE) AS unit_price,
            CAST(gross_amount AS DOUBLE) AS gross_amount,
            CAST(discount_amount AS DOUBLE) AS discount_amount
        FROM raw_order_items
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold_revenue_daily AS
        SELECT
            CAST(order_ts AS DATE) AS order_date,
            COUNT(*) AS orders,
            COUNT(DISTINCT customer_id) AS active_customers,
            ROUND(SUM(total_amount), 2) AS revenue,
            ROUND(AVG(total_amount), 2) AS average_order_value
        FROM silver_orders
        WHERE status IN ('paid', 'shipped', 'delivered')
        GROUP BY 1
        ORDER BY 1
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold_product_velocity AS
        SELECT
            i.sku,
            p.category,
            p.brand,
            SUM(i.quantity) AS units_sold,
            ROUND(SUM(i.gross_amount - i.discount_amount), 2) AS net_item_revenue,
            ROUND(AVG(CAST(p.margin_percent AS DOUBLE)), 3) AS avg_margin_percent
        FROM silver_order_items i
        JOIN raw_products p USING (sku)
        JOIN silver_orders o USING (order_id)
        WHERE o.status IN ('paid', 'shipped', 'delivered')
        GROUP BY 1, 2, 3
        ORDER BY net_item_revenue DESC
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold_customer_ltv AS
        SELECT
            c.customer_id,
            c.country,
            c.city,
            c.segment,
            COUNT(DISTINCT o.order_id) AS orders,
            ROUND(SUM(o.total_amount), 2) AS lifetime_value,
            MAX(o.order_ts) AS last_order_ts
        FROM raw_customers c
        JOIN silver_orders o USING (customer_id)
        WHERE o.status IN ('paid', 'shipped', 'delivered')
        GROUP BY 1, 2, 3, 4
        ORDER BY lifetime_value DESC
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold_fulfillment_sla AS
        SELECT
            carrier,
            warehouse_id,
            COUNT(*) AS shipments,
            ROUND(AVG(DATE_DIFF('hour', CAST(shipped_ts AS TIMESTAMP), CAST(delivered_ts AS TIMESTAMP))), 2) AS avg_delivery_hours,
            ROUND(AVG(CASE
                WHEN DATE_DIFF('day', CAST(shipped_ts AS TIMESTAMP), CAST(delivered_ts AS TIMESTAMP)) > CAST(promised_days AS INTEGER)
                THEN 1 ELSE 0 END), 4) AS sla_breach_rate
        FROM raw_shipments
        GROUP BY 1, 2
        ORDER BY sla_breach_rate DESC, shipments DESC
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold_marketing_attribution AS
        SELECT
            c.acquisition_channel,
            o.campaign_id,
            COUNT(DISTINCT o.order_id) AS orders,
            COUNT(DISTINCT o.customer_id) AS customers,
            ROUND(SUM(o.total_amount), 2) AS revenue
        FROM silver_orders o
        JOIN raw_customers c USING (customer_id)
        WHERE o.status IN ('paid', 'shipped', 'delivered')
        GROUP BY 1, 2
        ORDER BY revenue DESC
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE gold_inventory_risk AS
        SELECT
            i.snapshot_ts,
            i.sku,
            p.category,
            i.warehouse_id,
            CAST(i.on_hand AS INTEGER) AS on_hand,
            CAST(i.reorder_point AS INTEGER) AS reorder_point,
            CAST(i.inbound_qty AS INTEGER) AS inbound_qty,
            CASE WHEN CAST(i.on_hand AS INTEGER) <= CAST(i.reorder_point AS INTEGER) THEN true ELSE false END AS is_reorder_risk
        FROM raw_inventory_snapshots i
        JOIN raw_products p USING (sku)
        ORDER BY is_reorder_risk DESC, on_hand ASC
        """
    )

    tables = [
        "gold_revenue_daily",
        "gold_product_velocity",
        "gold_customer_ltv",
        "gold_fulfillment_sla",
        "gold_marketing_attribution",
        "gold_inventory_risk",
    ]

    if export_dir is not None:
        export_dir.mkdir(parents=True, exist_ok=True)
        for table in tables:
            con.execute(f"COPY {table} TO '{sql_path(export_dir / f'{table}.parquet')}' (FORMAT PARQUET)")

    row_counts = {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
    con.close()
    return {"db": str(db_path), "gold_tables": row_counts}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build AstraFlow DuckDB warehouse.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--db", type=Path, default=Path("data/warehouse/astraflow.duckdb"))
    parser.add_argument("--export-dir", type=Path, default=Path("data/lake/gold"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_warehouse(args.data_dir, args.db, args.export_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
