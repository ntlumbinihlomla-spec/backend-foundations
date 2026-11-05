# Example data

These small, fictional CSV files are safe to use for local demos and tests. They
are deliberately kept separate from uploaded files and runtime data stored under
`data/`.

## Single-file summary

From the repository root, run:

```bash
python -m calculator.app finance summary examples/sales_demo.csv amount
```

The CSV has `date`, `customer`, and `amount` columns. The command summarizes the
`amount` column and prints transaction count, total, average, highest, and lowest
sale.

## Folder batch summary

The `sales_data/` folder contains one CSV per month. Summarize all of them with:

```bash
python -m calculator.app finance batch examples/sales_data amount
```

Use these examples as input fixtures; commands that accept an output path should
write generated reports outside this directory so the sample data stays clean.
