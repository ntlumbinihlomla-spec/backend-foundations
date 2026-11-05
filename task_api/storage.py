import json
from pathlib import Path


class JSONFileTaskStore:
    def __init__(self, file_path):
        self.path = Path(file_path)

    def load(self):
        if not self.path.exists():
            return []

        with self.path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        if not isinstance(data, list):
            raise ValueError("Task data must be a JSON list")

        return data

    def save(self, tasks):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file_handle:
            json.dump(tasks, file_handle, indent=2)
