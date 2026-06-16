PYTHON ?= python3.11
DATA_DIR ?= data/raw
WAREHOUSE_DB ?= data/warehouse/astraflow.duckdb
REPORT ?= reports/quality_report.json

.PHONY: setup generate validate warehouse produce api dashboard test lint smoke clean compose-up compose-down

setup:
	$(PYTHON) -m pip install -e ".[dev]"

generate:
	PYTHONPATH=src $(PYTHON) -m astraflow.generator --days 7 --orders-per-day 500 --customers 2500 --products 250 --seed 42 --out $(DATA_DIR)

validate:
	PYTHONPATH=src $(PYTHON) -m astraflow.quality --data-dir $(DATA_DIR) --report $(REPORT)

warehouse:
	PYTHONPATH=src $(PYTHON) -m astraflow.warehouse --data-dir $(DATA_DIR) --db $(WAREHOUSE_DB) --export-dir data/lake/gold

produce:
	PYTHONPATH=src $(PYTHON) -m astraflow.producer --data-dir $(DATA_DIR) --bootstrap-servers localhost:19092

api:
	PYTHONPATH=src uvicorn astraflow.api:app --host 0.0.0.0 --port 8080 --reload

dashboard:
	PYTHONPATH=src streamlit run src/astraflow/dashboard.py --server.port 8501

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	ruff check src tests

smoke: generate validate warehouse test

compose-up:
	docker compose up -d redpanda console minio postgres

compose-down:
	docker compose down --remove-orphans

clean:
	rm -rf data/raw data/lake data/warehouse reports logs
