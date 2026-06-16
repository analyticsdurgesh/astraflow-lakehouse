from __future__ import annotations

import unittest

from astraflow.models import DATASET_FILES, PRIMARY_KEYS, REQUIRED_FIELDS


class ContractTests(unittest.TestCase):
    def test_every_dataset_has_file_key_and_required_fields(self) -> None:
        for dataset in DATASET_FILES:
            self.assertIn(dataset, PRIMARY_KEYS)
            self.assertIn(dataset, REQUIRED_FIELDS)
            self.assertIn(PRIMARY_KEYS[dataset], REQUIRED_FIELDS[dataset])


if __name__ == "__main__":
    unittest.main()
