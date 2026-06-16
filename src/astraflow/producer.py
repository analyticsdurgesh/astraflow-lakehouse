from __future__ import annotations

import argparse
import json
from pathlib import Path

from astraflow.io_utils import read_jsonl

EVENT_FILES = {
    "orders": "orders.jsonl",
    "order_items": "order_items.jsonl",
    "payments": "payments.jsonl",
    "shipments": "shipments.jsonl",
    "clickstream_events": "clickstream_events.jsonl",
    "inventory_snapshots": "inventory_snapshots.jsonl",
    "support_tickets": "support_tickets.jsonl",
}


def produce_events(data_dir: Path, bootstrap_servers: str, topic_prefix: str, dry_run: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {}
    producer = None
    if not dry_run:
        try:
            from confluent_kafka import Producer
        except ImportError as exc:
            raise RuntimeError("confluent-kafka is required for producing events") from exc
        producer = Producer({"bootstrap.servers": bootstrap_servers})

    for dataset, filename in EVENT_FILES.items():
        topic = f"{topic_prefix}.{dataset}"
        rows = read_jsonl(data_dir / filename)
        counts[topic] = len(rows)
        if dry_run:
            continue
        assert producer is not None
        for row in rows:
            key = str(row.get("order_id") or row.get("event_id") or row.get("snapshot_id"))
            producer.produce(topic, key=key, value=json.dumps(row, sort_keys=True).encode("utf-8"))
        producer.flush()

    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Produce generated AstraFlow events to Kafka/Redpanda.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--bootstrap-servers", default="localhost:19092")
    parser.add_argument("--topic-prefix", default="astraflow")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = produce_events(args.data_dir, args.bootstrap_servers, args.topic_prefix, args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
