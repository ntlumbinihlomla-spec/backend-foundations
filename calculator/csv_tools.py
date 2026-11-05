import csv
from pathlib import Path


def _validate_csv_file(filepath):
    path = Path(filepath)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("CSV file not found")
    return path


def count_rows(filepath):
    path = _validate_csv_file(filepath)
    with path.open(newline="", encoding="utf-8") as file_handle:
        return sum(1 for _ in csv.reader(file_handle))


def count_columns(filepath):
    path = _validate_csv_file(filepath)
    with path.open(newline="", encoding="utf-8") as file_handle:
        reader = csv.reader(file_handle)
        first_row = next(reader, None)
        if first_row is None:
            raise ValueError("CSV file is empty")
        return len(first_row)

