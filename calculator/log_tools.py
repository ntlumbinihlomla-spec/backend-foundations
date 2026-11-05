from pathlib import Path


def count_errors(filepath):
    path = Path(filepath)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("Log file not found")

    with path.open("r", encoding="utf-8") as file_handle:
        return sum(1 for line in file_handle if "error" in line.lower())

