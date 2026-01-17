import csv
from pathlib import Path

def summarize_csv_column(file_path, column_name):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("CSV file not found")

    values = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if column_name not in reader.fieldnames:
            raise ValueError("Column not found in CSV")

        for row in reader:
            try:
                values.append(float(row[column_name]))
            except ValueError:
                continue

    if not values:
        raise ValueError("No numeric data found")

    return {
        "rows": len(values),
        "sum": sum(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }
