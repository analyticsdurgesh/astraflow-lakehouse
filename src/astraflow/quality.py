from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from astraflow.io_utils import read_csv, read_jsonl
from astraflow.models import (
    DATASET_FILES,
    DELIVERY_STATUSES,
    ORDER_STATUSES,
    PAYMENT_STATUSES,
    PRIMARY_KEYS,
    REQUIRED_FIELDS,
)


@dataclass
class CheckResult:
    name: str
    status: str
    details: str
    failed_rows: int = 0


def pass_check(name: str, details: str) -> CheckResult:
    return CheckResult(name=name, status="pass", details=details)


def fail_check(name: str, details: str, failed_rows: int = 0) -> CheckResult:
    return CheckResult(name=name, status="fail", details=details, failed_rows=failed_rows)


def load_dataset(data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    loaded: dict[str, list[dict[str, Any]]] = {}
    for dataset, filename in DATASET_FILES.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required dataset file: {path}")
        loaded[dataset] = read_csv(path) if filename.endswith(".csv") else read_jsonl(path)
    return loaded


def check_required_fields(dataset: str, rows: list[dict[str, Any]]) -> CheckResult:
    missing = []
    required = REQUIRED_FIELDS[dataset]
    for idx, row in enumerate(rows):
        absent = [field for field in required if field not in row or row[field] in ("", None)]
        if absent:
            missing.append({"row": idx, "fields": absent})
    if missing:
        return fail_check(
            f"{dataset}.required_fields",
            f"{len(missing)} rows are missing required fields",
            len(missing),
        )
    return pass_check(f"{dataset}.required_fields", f"{len(rows)} rows include required fields")


def check_unique_key(dataset: str, rows: list[dict[str, Any]]) -> CheckResult:
    key = PRIMARY_KEYS[dataset]
    seen: set[str] = set()
    duplicates = 0
    for row in rows:
        value = str(row.get(key, ""))
        if value in seen:
            duplicates += 1
        seen.add(value)
    if duplicates:
        return fail_check(f"{dataset}.unique_{key}", f"{duplicates} duplicate keys found", duplicates)
    return pass_check(f"{dataset}.unique_{key}", f"{len(seen)} unique keys found")


def check_subset(
    name: str,
    rows: list[dict[str, Any]],
    field: str,
    allowed: set[str],
) -> CheckResult:
    bad = [row for row in rows if str(row.get(field)) not in allowed]
    if bad:
        return fail_check(name, f"{len(bad)} rows have invalid {field}", len(bad))
    return pass_check(name, f"All {len(rows)} rows have valid {field}")


def check_relation(
    name: str,
    child_rows: list[dict[str, Any]],
    child_field: str,
    parent_values: set[str],
) -> CheckResult:
    bad = [row for row in child_rows if str(row.get(child_field)) not in parent_values]
    if bad:
        return fail_check(name, f"{len(bad)} rows failed referential integrity", len(bad))
    return pass_check(name, f"All {len(child_rows)} rows passed referential integrity")


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def check_numeric_rules(data: dict[str, list[dict[str, Any]]]) -> list[CheckResult]:
    checks: list[CheckResult] = []

    bad_orders = [row for row in data["orders"] if to_float(row.get("total_amount")) < 0]
    checks.append(
        fail_check("orders.total_amount_non_negative", "Negative order totals found", len(bad_orders))
        if bad_orders
        else pass_check("orders.total_amount_non_negative", "Order totals are non-negative")
    )

    bad_items = [row for row in data["order_items"] if to_float(row.get("quantity")) <= 0]
    checks.append(
        fail_check("order_items.quantity_positive", "Non-positive quantities found", len(bad_items))
        if bad_items
        else pass_check("order_items.quantity_positive", "Order quantities are positive")
    )

    bad_risk = [
        row
        for row in data["payments"]
        if not 0 <= to_float(row.get("risk_score")) <= 1 or to_float(row.get("amount")) < 0
    ]
    checks.append(
        fail_check("payments.amount_and_risk_range", "Invalid amount or risk score found", len(bad_risk))
        if bad_risk
        else pass_check("payments.amount_and_risk_range", "Payment amounts and risk scores are valid")
    )

    bad_latency = [
        row for row in data["clickstream_events"] if not 0 <= to_float(row.get("page_latency_ms")) <= 10000
    ]
    checks.append(
        fail_check("clickstream.page_latency_range", "Invalid page latency found", len(bad_latency))
        if bad_latency
        else pass_check("clickstream.page_latency_range", "Page latency is within accepted range")
    )

    bad_inventory = [
        row
        for row in data["inventory_snapshots"]
        if min(to_float(row.get("on_hand")), to_float(row.get("reorder_point")), to_float(row.get("inbound_qty"))) < 0
    ]
    checks.append(
        fail_check("inventory.non_negative_quantities", "Negative inventory values found", len(bad_inventory))
        if bad_inventory
        else pass_check("inventory.non_negative_quantities", "Inventory quantities are non-negative")
    )

    return checks


def validate_dataset(data_dir: Path) -> dict[str, Any]:
    data = load_dataset(data_dir)
    checks: list[CheckResult] = []

    for dataset, rows in data.items():
        checks.append(pass_check(f"{dataset}.row_count", f"{len(rows)} rows loaded") if rows else fail_check(f"{dataset}.row_count", "No rows found"))
        checks.append(check_required_fields(dataset, rows))
        checks.append(check_unique_key(dataset, rows))

    customer_ids = {str(row["customer_id"]) for row in data["customers"]}
    product_ids = {str(row["sku"]) for row in data["products"]}
    order_ids = {str(row["order_id"]) for row in data["orders"]}

    checks.extend(
        [
            check_subset("orders.status_values", data["orders"], "status", ORDER_STATUSES),
            check_subset("payments.status_values", data["payments"], "status", PAYMENT_STATUSES),
            check_subset("shipments.delivery_status_values", data["shipments"], "delivery_status", DELIVERY_STATUSES),
            check_relation("orders.customer_fk", data["orders"], "customer_id", customer_ids),
            check_relation("order_items.order_fk", data["order_items"], "order_id", order_ids),
            check_relation("order_items.product_fk", data["order_items"], "sku", product_ids),
            check_relation("payments.order_fk", data["payments"], "order_id", order_ids),
            check_relation("shipments.order_fk", data["shipments"], "order_id", order_ids),
            check_relation("clickstream.customer_fk", data["clickstream_events"], "customer_id", customer_ids),
            check_relation("clickstream.product_fk", data["clickstream_events"], "sku", product_ids),
            check_relation("inventory.product_fk", data["inventory_snapshots"], "sku", product_ids),
            check_relation("support_tickets.order_fk", data["support_tickets"], "order_id", order_ids),
            check_relation("support_tickets.customer_fk", data["support_tickets"], "customer_id", customer_ids),
        ]
    )
    checks.extend(check_numeric_rules(data))

    status = "pass" if all(check.status == "pass" for check in checks) else "fail"
    return {
        "project": "astraflow-lakehouse",
        "status": status,
        "data_dir": str(data_dir),
        "summary": {
            "checks": len(checks),
            "passed": sum(1 for check in checks if check.status == "pass"),
            "failed": sum(1 for check in checks if check.status == "fail"),
        },
        "checks": [asdict(check) for check in checks],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AstraFlow generated data.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--report", type=Path, default=Path("reports/quality_report.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = validate_dataset(args.data_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
