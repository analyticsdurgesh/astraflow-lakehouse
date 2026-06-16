# Architecture

AstraFlow Lakehouse is organized around clear data-platform boundaries: source simulation, ingestion, storage, validation, transformation, orchestration, and serving.

## System Goals

- Demonstrate batch and streaming data engineering in one repository.
- Keep the local developer loop fast.
- Use real architectural patterns without requiring cloud accounts.
- Make every data contract and derived metric explainable.
- Provide a path from local demo to production deployment.

## Data Flow

1. The Python generator creates deterministic commerce datasets in `data/raw`.
2. The producer can publish event files to Redpanda topics.
3. Spark Structured Streaming reads Kafka topics and writes bronze Parquet.
4. Quality gates validate generated/raw data before downstream marts run.
5. DuckDB builds silver and gold tables for serving and local analytics.
6. FastAPI exposes the most useful gold metrics.
7. Streamlit renders an executive dashboard.
8. Airflow can orchestrate generation, validation, warehouse build, and tests.

## Lakehouse Layers

### Bronze

Bronze contains immutable raw events and dimensions. It keeps source field names and event timestamps. In production this layer should be append-only and partitioned by ingestion date.

### Silver

Silver contains typed, deduplicated, contract-valid records. This is where late-event handling, standard naming, referential integrity, and currency normalization belong.

### Gold

Gold contains business-ready marts:

- revenue by day
- product velocity
- customer lifetime value
- fulfillment SLA
- marketing attribution
- inventory risk

## Reliability Patterns

- Deterministic data generation by seed for reproducible tests.
- Quality report emitted as machine-readable JSON.
- Clear failure exits for quality gate violations.
- Warehouse build is idempotent with `CREATE OR REPLACE`.
- Kafka topic naming is centralized in config.
- API queries are read-only against curated gold tables.

## Production Migration

| Local | Production Option |
| --- | --- |
| Redpanda container | Confluent Cloud, MSK, Pub/Sub plus Dataflow |
| MinIO | S3, GCS, ADLS |
| DuckDB | BigQuery, Snowflake, Databricks SQL, Trino |
| Local Spark | Databricks, EMR, DataProc, Spark on Kubernetes |
| Airflow DAG file | Managed Airflow, Dagster, Prefect |
| JSON quality report | Quality dashboard, Slack alerts, CI/CD gate |

## Failure Handling

- Bad contracts fail before warehouse build.
- Missing raw files fail fast with actionable messages.
- API starts even when the warehouse is missing, but `/health` reports degraded status.
- Streaming producer supports dry-run mode for demos without Kafka.
