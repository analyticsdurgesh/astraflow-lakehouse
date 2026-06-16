from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from astraflow.generator import generate_dataset
from astraflow.quality import validate_dataset


class QualityTests(unittest.TestCase):
    def test_generated_data_passes_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            generate_dataset(
                out_dir=out_dir,
                days=2,
                orders_per_day=20,
                customers_count=50,
                products_count=12,
                seed=44,
            )

            report = validate_dataset(out_dir)

            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertGreater(report["summary"]["passed"], 20)


if __name__ == "__main__":
    unittest.main()
