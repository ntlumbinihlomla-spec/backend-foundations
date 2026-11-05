from copy import deepcopy
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TaskService:
    def __init__(self, store):
        self.store = store

    def list_tasks(self):
        return self.store.load()

    def get_task(self, task_id):
        for task in self.store.load():
            if task["id"] == task_id:
                return task
        return None

    def create_task(self, title, description=""):
        cleaned_title = title.strip()
        if not cleaned_title:
            raise ValueError("Title is required")

        tasks = self.store.load()
        timestamp = utc_now()
        task = {
            "id": self._next_id(tasks),
            "title": cleaned_title,
            "description": description.strip(),
            "completed": False,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        tasks.append(task)
        self.store.save(tasks)
        return deepcopy(task)

    def update_task(self, task_id, updates):
        tasks = self.store.load()
        for task in tasks:
            if task["id"] != task_id:
                continue

            if "title" in updates:
                cleaned_title = updates["title"].strip()
                if not cleaned_title:
                    raise ValueError("Title cannot be empty")
                task["title"] = cleaned_title

            if "description" in updates:
                task["description"] = str(updates["description"]).strip()

            if "completed" in updates:
                if not isinstance(updates["completed"], bool):
                    raise ValueError("Completed must be true or false")
                task["completed"] = updates["completed"]

            task["updated_at"] = utc_now()
            self.store.save(tasks)
            return deepcopy(task)

        return None

    def delete_task(self, task_id):
        tasks = self.store.load()
        remaining = [task for task in tasks if task["id"] != task_id]
        if len(remaining) == len(tasks):
            return False

        self.store.save(remaining)
        return True

    @staticmethod
    def _next_id(tasks):
        if not tasks:
            return 1
        return max(task["id"] for task in tasks) + 1
