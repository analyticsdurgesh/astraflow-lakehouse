from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from astraflow.io_utils import write_csv, write_jsonl

COUNTRIES = {
    "US": ["Austin", "Seattle", "New York", "San Francisco", "Chicago"],
    "IN": ["Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi"],
    "GB": ["London", "Manchester", "Bristol", "Leeds"],
    "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt"],
    "SG": ["Singapore"],
}

SEGMENTS = ["student", "professional", "founder", "enterprise", "creator"]
CHANNELS = ["organic", "paid_search", "paid_social", "email", "affiliate", "direct"]
ORDER_CHANNELS = ["web", "ios", "android", "marketplace"]
DEVICES = ["desktop", "mobile", "tablet"]
CATEGORIES = ["laptop", "audio", "wearable", "home-office", "developer-tool", "learning"]
BRANDS = ["Northstar", "Volt", "Kairo", "Luma", "Orion", "Apex"]
SUPPLIER_REGIONS = ["north-america", "europe", "india", "southeast-asia"]
PAYMENT_METHODS = ["card", "upi", "wallet", "bank_transfer", "paypal"]
CARRIERS = ["ShipFast", "AeroPost", "MetroCourier", "ParcelJet"]
WAREHOUSES = ["wh_us_west", "wh_us_east", "wh_in_south", "wh_eu_central"]
EVENT_TYPES = ["product_view", "add_to_cart", "checkout_start", "coupon_apply", "search", "wishlist"]
ISSUE_TYPES = ["late_delivery", "damaged_item", "payment_issue", "wrong_item", "return_request"]


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def money(value: float) -> float:
    return round(value + 1e-8, 2)


def weighted_choice(rng: random.Random, weighted: list[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in weighted)
    marker = rng.random() * total
    upto = 0.0
    for value, weight in weighted:
        if upto + weight >= marker:
            return value
        upto += weight
    return weighted[-1][0]


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_DNS, raw).hex[:14]}"


def build_customers(rng: random.Random, count: int, start: datetime) -> list[dict[str, Any]]:
    customers = []
    country_keys = list(COUNTRIES)
    for idx in range(count):
        country = rng.choice(country_keys)
        signup_ts = start - timedelta(days=rng.randint(1, 730), minutes=rng.randint(0, 1440))
        customers.append(
            {
                "customer_id": stable_id("cus", idx, country),
                "signup_ts": iso(signup_ts),
                "country": country,
                "city": rng.choice(COUNTRIES[country]),
                "segment": rng.choice(SEGMENTS),
                "acquisition_channel": rng.choice(CHANNELS),
            }
        )
    return customers


def build_products(rng: random.Random, count: int) -> list[dict[str, Any]]:
    products = []
    for idx in range(count):
        category = rng.choice(CATEGORIES)
        base_price = {
            "laptop": 950,
            "audio": 120,
            "wearable": 210,
            "home-office": 350,
            "developer-tool": 79,
            "learning": 49,
        }[category]
        products.append(
            {
                "sku": stable_id("sku", category, idx),
                "category": category,
                "brand": rng.choice(BRANDS),
                "unit_price": money(base_price * rng.uniform(0.65, 1.8)),
                "margin_percent": round(rng.uniform(0.18, 0.62), 3),
                "supplier_region": rng.choice(SUPPLIER_REGIONS),
            }
        )
    return products


def build_orders(
    rng: random.Random,
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    days: int,
    orders_per_day: int,
    start: datetime,
) -> dict[str, list[dict[str, Any]]]:
    orders: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    payments: list[dict[str, Any]] = []
    shipments: list[dict[str, Any]] = []
    tickets: list[dict[str, Any]] = []

    status_weights = [
        ("created", 0.05),
        ("paid", 0.14),
        ("shipped", 0.18),
        ("delivered", 0.51),
        ("cancelled", 0.08),
        ("returned", 0.04),
    ]

    for day in range(days):
        order_date = start + timedelta(days=day)
        for n in range(orders_per_day):
            customer = rng.choice(customers)
            order_ts = order_date + timedelta(minutes=rng.randint(0, 1439), seconds=rng.randint(0, 59))
            order_id = stable_id("ord", day, n, customer["customer_id"])
            status = weighted_choice(rng, status_weights)
            item_count = rng.randint(1, 4)
            chosen_products = rng.sample(products, k=min(item_count, len(products)))

            subtotal = 0.0
            order_discount = 0.0
            for item_idx, product in enumerate(chosen_products):
                quantity = rng.randint(1, 3)
                unit_price = float(product["unit_price"])
                gross_amount = money(unit_price * quantity)
                discount_amount = money(gross_amount * rng.choice([0.0, 0.0, 0.05, 0.10, 0.15]))
                subtotal += gross_amount
                order_discount += discount_amount
                items.append(
                    {
                        "order_item_id": stable_id("itm", order_id, item_idx),
                        "order_id": order_id,
                        "sku": product["sku"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "gross_amount": gross_amount,
                        "discount_amount": discount_amount,
                    }
                )

            shipping_fee = 0.0 if subtotal > 100 else 5.99
            tax = money((subtotal - order_discount) * 0.0825)
            total_amount = money(subtotal - order_discount + shipping_fee + tax)
            campaign_id = stable_id("cmp", customer["acquisition_channel"], order_ts.month)
            device_type = rng.choice(DEVICES)

            orders.append(
                {
                    "order_id": order_id,
                    "customer_id": customer["customer_id"],
                    "order_ts": iso(order_ts),
                    "channel": rng.choice(ORDER_CHANNELS),
                    "status": status,
                    "currency": "USD",
                    "subtotal": money(subtotal),
                    "discount": money(order_discount),
                    "shipping_fee": shipping_fee,
                    "tax": tax,
                    "total_amount": total_amount,
                    "campaign_id": campaign_id,
                    "device_type": device_type,
                }
            )

            payment_status = "failed" if status == "cancelled" else rng.choice(["authorized", "captured", "captured"])
            if status == "returned":
                payment_status = "refunded"
            payments.append(
                {
                    "payment_id": stable_id("pay", order_id),
                    "order_id": order_id,
                    "payment_ts": iso(order_ts + timedelta(minutes=rng.randint(1, 20))),
                    "method": rng.choice(PAYMENT_METHODS),
                    "status": payment_status,
                    "amount": total_amount,
                    "risk_score": round(rng.betavariate(2, 10), 4),
                }
            )

            if status in {"shipped", "delivered", "returned"}:
                promised_days = rng.choice([2, 3, 5, 7])
                shipped_ts = order_ts + timedelta(hours=rng.randint(3, 36))
                delivery_delay = rng.randint(1, promised_days + rng.choice([0, 0, 1, 3]))
                delivered_ts = shipped_ts + timedelta(days=delivery_delay, hours=rng.randint(0, 12))
                delivery_status = "delivered" if status in {"delivered", "returned"} else "in_transit"
                if delivery_delay > promised_days:
                    delivery_status = "delayed"
                if status == "returned":
                    delivery_status = "returned"
                shipments.append(
                    {
                        "shipment_id": stable_id("shp", order_id),
                        "order_id": order_id,
                        "warehouse_id": rng.choice(WAREHOUSES),
                        "shipped_ts": iso(shipped_ts),
                        "delivered_ts": iso(delivered_ts),
                        "carrier": rng.choice(CARRIERS),
                        "delivery_status": delivery_status,
                        "promised_days": promised_days,
                    }
                )

            if rng.random() < 0.08:
                tickets.append(
                    {
                        "ticket_id": stable_id("tic", order_id),
                        "order_id": order_id,
                        "customer_id": customer["customer_id"],
                        "created_ts": iso(order_ts + timedelta(days=rng.randint(1, 9))),
                        "issue_type": rng.choice(ISSUE_TYPES),
                        "priority": rng.choice(["low", "medium", "high"]),
                        "status": rng.choice(["open", "pending", "resolved"]),
                    }
                )

    return {
        "orders": orders,
        "order_items": items,
        "payments": payments,
        "shipments": shipments,
        "support_tickets": tickets,
    }


def build_clickstream(
    rng: random.Random,
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    days: int,
    events_per_day: int,
    start: datetime,
) -> list[dict[str, Any]]:
    events = []
    for day in range(days):
        event_date = start + timedelta(days=day)
        for n in range(events_per_day):
            customer = rng.choice(customers)
            event_ts = event_date + timedelta(minutes=rng.randint(0, 1439), seconds=rng.randint(0, 59))
            product = rng.choice(products)
            channel = rng.choice(CHANNELS)
            events.append(
                {
                    "event_id": stable_id("evt", day, n, customer["customer_id"], event_ts),
                    "event_ts": iso(event_ts),
                    "customer_id": customer["customer_id"],
                    "session_id": stable_id("ses", customer["customer_id"], day, rng.randint(1, 8)),
                    "event_type": rng.choice(EVENT_TYPES),
                    "sku": product["sku"],
                    "campaign_id": stable_id("cmp", channel, event_ts.month),
                    "device_type": rng.choice(DEVICES),
                    "page_latency_ms": rng.randint(40, 4500),
                }
            )
    return events


def build_inventory(
    rng: random.Random,
    products: list[dict[str, Any]],
    days: int,
    start: datetime,
) -> list[dict[str, Any]]:
    snapshots = []
    for day in range(days):
        snapshot_ts = start + timedelta(days=day, hours=6)
        for product in products:
            for warehouse_id in WAREHOUSES:
                reorder_point = rng.randint(15, 120)
                on_hand = max(0, int(rng.gauss(reorder_point * 2.4, reorder_point * 1.1)))
                snapshots.append(
                    {
                        "snapshot_id": stable_id("inv", product["sku"], warehouse_id, day),
                        "snapshot_ts": iso(snapshot_ts),
                        "sku": product["sku"],
                        "warehouse_id": warehouse_id,
                        "on_hand": on_hand,
                        "reorder_point": reorder_point,
                        "inbound_qty": rng.choice([0, 0, 20, 50, 100, 250]),
                    }
                )
    return snapshots


def generate_dataset(
    out_dir: Path,
    days: int = 7,
    orders_per_day: int = 500,
    customers_count: int = 2500,
    products_count: int = 250,
    seed: int = 42,
    start_date: str = "2026-01-01",
) -> dict[str, Any]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)

    customers = build_customers(rng, customers_count, start)
    products = build_products(rng, products_count)
    order_bundle = build_orders(rng, customers, products, days, orders_per_day, start)
    clickstream = build_clickstream(rng, customers, products, days, orders_per_day * 5, start)
    inventory = build_inventory(rng, products, days, start)

    write_csv(
        out_dir / "customers.csv",
        customers,
        ["customer_id", "signup_ts", "country", "city", "segment", "acquisition_channel"],
    )
    write_csv(
        out_dir / "products.csv",
        products,
        ["sku", "category", "brand", "unit_price", "margin_percent", "supplier_region"],
    )

    counts = {
        "customers": len(customers),
        "products": len(products),
        "orders": write_jsonl(out_dir / "orders.jsonl", order_bundle["orders"]),
        "order_items": write_jsonl(out_dir / "order_items.jsonl", order_bundle["order_items"]),
        "payments": write_jsonl(out_dir / "payments.jsonl", order_bundle["payments"]),
        "shipments": write_jsonl(out_dir / "shipments.jsonl", order_bundle["shipments"]),
        "clickstream_events": write_jsonl(out_dir / "clickstream_events.jsonl", clickstream),
        "inventory_snapshots": write_jsonl(out_dir / "inventory_snapshots.jsonl", inventory),
        "support_tickets": write_jsonl(out_dir / "support_tickets.jsonl", order_bundle["support_tickets"]),
    }
    manifest = {
        "project": "astraflow-lakehouse",
        "seed": seed,
        "start_date": start_date,
        "days": days,
        "orders_per_day": orders_per_day,
        "counts": counts,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic AstraFlow commerce data.")
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--orders-per-day", type=int, default=500)
    parser.add_argument("--customers", type=int, default=2500)
    parser.add_argument("--products", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-date", default="2026-01-01")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = generate_dataset(
        out_dir=args.out,
        days=args.days,
        orders_per_day=args.orders_per_day,
        customers_count=args.customers,
        products_count=args.products,
        seed=args.seed,
        start_date=args.start_date,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
