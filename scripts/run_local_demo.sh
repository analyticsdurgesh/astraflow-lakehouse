#!/usr/bin/env bash
set -euo pipefail

python -m astraflow.generator --days 3 --orders-per-day 250 --customers 1000 --products 120 --seed 42 --out data/raw
python -m astraflow.quality --data-dir data/raw --report reports/quality_report.json
python -m astraflow.warehouse --data-dir data/raw --db data/warehouse/astraflow.duckdb --export-dir data/lake/gold
python -m unittest discover -s tests -v
