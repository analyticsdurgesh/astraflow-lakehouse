from __future__ import annotations

import os
from pathlib import Path

import duckdb
import streamlit as st


def read_table(db_path: Path, table: str):
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(f"SELECT * FROM {table}").fetchdf()


st.set_page_config(page_title="AstraFlow Lakehouse", layout="wide")
st.title("AstraFlow Lakehouse")

warehouse = Path(os.getenv("ASTRAFLOW_WAREHOUSE_DB", "data/warehouse/astraflow.duckdb"))
if not warehouse.exists():
    st.error(f"Warehouse not found at {warehouse}. Run `make smoke` first.")
    st.stop()

revenue = read_table(warehouse, "gold_revenue_daily")
product_velocity = read_table(warehouse, "gold_product_velocity")
fulfillment = read_table(warehouse, "gold_fulfillment_sla")
inventory = read_table(warehouse, "gold_inventory_risk")

total_revenue = float(revenue["revenue"].sum()) if not revenue.empty else 0.0
total_orders = int(revenue["orders"].sum()) if not revenue.empty else 0
avg_order_value = total_revenue / total_orders if total_orders else 0
reorder_risk = int(inventory["is_reorder_risk"].sum()) if not inventory.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Revenue", f"${total_revenue:,.0f}")
col2.metric("Orders", f"{total_orders:,}")
col3.metric("AOV", f"${avg_order_value:,.2f}")
col4.metric("Reorder Risks", f"{reorder_risk:,}")

left, right = st.columns(2)
with left:
    st.subheader("Daily Revenue")
    st.line_chart(revenue.set_index("order_date")["revenue"])

with right:
    st.subheader("Top Product Velocity")
    st.dataframe(product_velocity.head(20), use_container_width=True)

st.subheader("Fulfillment SLA")
st.dataframe(fulfillment, use_container_width=True)

st.subheader("Inventory Risk")
st.dataframe(inventory.head(50), use_container_width=True)
