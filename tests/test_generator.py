from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from astraflow.generator import generate_dataset
from astraflow.io_utils import read_csv, read_jsonl


class GeneratorTests(unittest.TestCase):
    def test_generate_dataset_creates_expected_files_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            manifest = generate_dataset(
                out_dir=out_dir,
                days=2,
                orders_per_day=10,
                customers_count=30,
                products_count=8,
                seed=123,
            )

            self.assertEqual(manifest["counts"]["orders"], 20)
            self.assertEqual(len(read_csv(out_dir / "customers.csv")), 30)
            self.assertEqual(len(read_csv(out_dir / "products.csv")), 8)
            self.assertEqual(len(read_jsonl(out_dir / "orders.jsonl")), 20)
            self.assertTrue((out_dir / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
