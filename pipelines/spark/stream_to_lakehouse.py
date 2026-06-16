from __future__ import annotations

import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType


def spark() -> SparkSession:
    return (
        SparkSession.builder.appName("astraflow-stream-to-lakehouse")
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "4"))
        .getOrCreate()
    )


ORDER_SCHEMA = StructType(
    [
        StructField("order_id", StringType()),
        StructField("customer_id", StringType()),
        StructField("order_ts", StringType()),
        StructField("channel", StringType()),
        StructField("status", StringType()),
        StructField("currency", StringType()),
        StructField("subtotal", DoubleType()),
        StructField("discount", DoubleType()),
        StructField("shipping_fee", DoubleType()),
        StructField("tax", DoubleType()),
        StructField("total_amount", DoubleType()),
        StructField("campaign_id", StringType()),
        StructField("device_type", StringType()),
    ]
)

ITEM_SCHEMA = StructType(
    [
        StructField("order_item_id", StringType()),
        StructField("order_id", StringType()),
        StructField("sku", StringType()),
        StructField("quantity", IntegerType()),
        StructField("unit_price", DoubleType()),
        StructField("gross_amount", DoubleType()),
        StructField("discount_amount", DoubleType()),
    ]
)


def read_topic(session: SparkSession, bootstrap: str, topic: str):
    return (
        session.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .load()
    )


def parse_json(stream, schema: StructType):
    return stream.select(from_json(col("value").cast("string"), schema).alias("payload")).select("payload.*")


def write_parquet(stream, path: str, checkpoint: str):
    return (
        stream.writeStream.format("parquet")
        .option("path", path)
        .option("checkpointLocation", checkpoint)
        .outputMode("append")
        .start()
    )


def main() -> None:
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    lake_dir = os.getenv("ASTRAFLOW_LAKE_DIR", "data/lake")
    prefix = os.getenv("KAFKA_TOPIC_PREFIX", "astraflow")
    session = spark()

    orders = parse_json(read_topic(session, bootstrap, f"{prefix}.orders"), ORDER_SCHEMA).withColumn(
        "order_ts", to_timestamp("order_ts")
    )
    valid_orders = orders.filter(col("order_id").isNotNull() & col("customer_id").isNotNull())

    items = parse_json(read_topic(session, bootstrap, f"{prefix}.order_items"), ITEM_SCHEMA).filter(
        col("quantity") > 0
    )

    queries = [
        write_parquet(valid_orders, f"{lake_dir}/bronze/orders", f"{lake_dir}/checkpoints/orders"),
        write_parquet(items, f"{lake_dir}/bronze/order_items", f"{lake_dir}/checkpoints/order_items"),
    ]

    for query in queries:
        query.awaitTermination()


if __name__ == "__main__":
    main()
