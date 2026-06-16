# Operations

## Local Runbook

1. Start dependencies:

   ```bash
   docker compose up -d redpanda console minio postgres
   ```

2. Generate data:

   ```bash
   make generate
   ```

3. Validate data:

   ```bash
   make validate
   ```

4. Build warehouse:

   ```bash
   make warehouse
   ```

5. Serve metrics:

   ```bash
   make api
   ```

## Data Quality Gate

The quality runner writes `reports/quality_report.json`.

Status values:

- `pass`: all checks passed.
- `fail`: at least one blocking check failed.

Quality failures should block downstream marts in CI and orchestration.

## Monitoring Ideas

Recommended production metrics:

- Kafka consumer lag by topic and partition.
- Bronze to silver processing delay.
- Gold mart freshness.
- Quality pass/fail count by dataset.
- API p95 latency.
- Warehouse build duration.
- Null rate and duplicate rate by key dataset.

## Backfill Strategy

For historical backfills:

1. Generate or load raw files into a date-partitioned bronze path.
2. Run quality checks over the target date range.
3. Rebuild affected silver partitions.
4. Rebuild gold marts from impacted silver partitions.
5. Compare row counts, revenue totals, and SLA metrics before publishing.

## Incident Response

| Symptom | Likely Cause | First Action |
| --- | --- | --- |
| API returns empty marts | Warehouse was not built | Run `make warehouse` |
| Quality gate fails | Contract or referential issue | Open `reports/quality_report.json` |
| Producer cannot connect | Redpanda is down | Run `docker compose ps` |
| Dashboard fails | Missing DuckDB file | Run `make smoke` |
| Spark job cannot resolve Kafka | Missing Spark Kafka package | Use the package coordinates in `pipelines/spark/stream_to_lakehouse.py` |
