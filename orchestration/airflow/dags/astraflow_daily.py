from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/astraflow-lakehouse"

with DAG(
    dag_id="astraflow_daily_lakehouse",
    description="Generate, validate, and publish AstraFlow daily lakehouse marts.",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["data-engineering", "lakehouse", "quality"],
) as dag:
    generate = BashOperator(
        task_id="generate_data",
        bash_command=f"cd {PROJECT_DIR} && PYTHONPATH=src python -m astraflow.generator --days 1 --orders-per-day 1000 --out data/raw",
    )

    validate = BashOperator(
        task_id="validate_contracts",
        bash_command=f"cd {PROJECT_DIR} && PYTHONPATH=src python -m astraflow.quality --data-dir data/raw --report reports/quality_report.json",
    )

    warehouse = BashOperator(
        task_id="build_gold_marts",
        bash_command=f"cd {PROJECT_DIR} && PYTHONPATH=src python -m astraflow.warehouse --data-dir data/raw --db data/warehouse/astraflow.duckdb --export-dir data/lake/gold",
    )

    tests = BashOperator(
        task_id="run_unit_tests",
        bash_command=f"cd {PROJECT_DIR} && PYTHONPATH=src python -m unittest discover -s tests -v",
    )

    generate >> validate >> warehouse >> tests
