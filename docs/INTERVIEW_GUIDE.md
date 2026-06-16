# Interview Guide

Use this project to explain senior-level data engineering decisions clearly.

## High-Impact Talking Points

- I created the dataset generator, so the project is reproducible and not dependent on third-party downloads.
- I separated raw ingestion, quality gates, warehouse build, and serving to mirror production ownership boundaries.
- I used Redpanda for Kafka-compatible streaming because it is lightweight for local demos.
- I used DuckDB for local analytical serving because it is fast, embedded, and easy to run in CI.
- I documented the production migration path to Snowflake, BigQuery, Databricks, S3, GCS, and managed Kafka.

## Questions You Can Answer

### How would this scale?

Move object storage to S3/GCS, run Spark on a managed cluster, store curated tables in Iceberg/Delta, serve marts through Trino/Snowflake/BigQuery, and promote quality gates into orchestration.

### How do you handle bad data?

Contracts are checked before warehouse build. Blocking issues produce a machine-readable quality report and a non-zero exit code.

### Why synthetic data?

It removes licensing issues, protects privacy, and makes CI deterministic while still modeling realistic domain relationships.

### Where would you add observability?

Kafka lag, batch duration, freshness, duplicate rate, null rate, SLA breach rate, API latency, and mart row counts.

### How would you improve reliability?

Add schema registry, table format ACID guarantees, checkpointed Spark jobs, dead-letter queues, lineage metadata, alerting, and replayable backfills.
