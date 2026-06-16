# Sample Data

Run this command to regenerate a small sample dataset:

```bash
PYTHONPATH=src python -m astraflow.generator --days 2 --orders-per-day 50 --customers 120 --products 25 --seed 7 --out data/sample
```

The main generated data path is `data/raw`, which is ignored by Git to keep the repository lightweight.
