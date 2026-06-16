from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="AstraFlow Metrics API",
    version="0.1.0",
    description="Read-only API over AstraFlow gold marts.",
)

TABLES = {
    "revenue-daily": "gold_revenue_daily",
    "product-velocity": "gold_product_velocity",
    "customer-ltv": "gold_customer_ltv",
    "fulfillment-sla": "gold_fulfillment_sla",
    "marketing-attribution": "gold_marketing_attribution",
    "inventory-risk": "gold_inventory_risk",
}


def db_path() -> Path:
    return Path(os.getenv("ASTRAFLOW_WAREHOUSE_DB", "data/warehouse/astraflow.duckdb"))


def query_table(table: str, limit: int) -> list[dict[str, Any]]:
    try:
        import duckdb
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="DuckDB is not installed") from exc

    path = db_path()
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Warehouse not found at {path}. Run make warehouse.")

    con = duckdb.connect(str(path), read_only=True)
    try:
        result = con.execute(f"SELECT * FROM {table} LIMIT ?", [limit])
        columns = [column[0] for column in result.description]
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
    finally:
        con.close()


@app.get("/health")
def health() -> dict[str, Any]:
    path = db_path()
    return {
        "status": "ok" if path.exists() else "degraded",
        "warehouse_db": str(path),
        "warehouse_exists": path.exists(),
    }


@app.get("/metrics/{metric_name}")
def metric(metric_name: str, limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, Any]]:
    table = TABLES.get(metric_name)
    if table is None:
        raise HTTPException(status_code=404, detail=f"Unknown metric: {metric_name}")
    return query_table(table, limit)
