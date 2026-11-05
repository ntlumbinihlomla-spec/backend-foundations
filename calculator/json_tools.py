import json
from pathlib import Path


def _validate_json_file(filepath):
    path = Path(filepath)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("JSON file not found")
    return path


def pretty_print_json(filepath):
    path = _validate_json_file(filepath)
    with path.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    return json.dumps(data, indent=4)


def count_keys(filepath):
    path = _validate_json_file(filepath)
    with path.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    if isinstance(data, dict):
        return len(data.keys())
    return 0
