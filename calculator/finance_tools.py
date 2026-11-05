import csv
import os
from pathlib import Path


def batch_summarize(folder, column):
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError("Folder does not exist")

    results = []
    grand_total = 0

    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            path = folder_path / file

            summary = summarize_csv_column(path, column)

            total = summary["sum"]
            grand_total += total

            results.append((file, total))

    return results, grand_total


def get_csv_columns(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("CSV file not found")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or []


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
