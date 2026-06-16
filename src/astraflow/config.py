from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    env: str
    data_dir: Path
    lake_dir: Path
    warehouse_db: Path
    kafka_bootstrap_servers: str
    kafka_topic_prefix: str


def load_settings() -> Settings:
    return Settings(
        env=os.getenv("ASTRAFLOW_ENV", "local"),
        data_dir=Path(os.getenv("ASTRAFLOW_DATA_DIR", "data/raw")),
        lake_dir=Path(os.getenv("ASTRAFLOW_LAKE_DIR", "data/lake")),
        warehouse_db=Path(os.getenv("ASTRAFLOW_WAREHOUSE_DB", "data/warehouse/astraflow.duckdb")),
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),
        kafka_topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "astraflow"),
    )
