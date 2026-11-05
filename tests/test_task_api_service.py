import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from task_api.service import TaskService
from task_api.storage import JSONFileTaskStore


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestTaskService(unittest.TestCase):
    def test_create_task_persists_and_sets_defaults(self):
        temp_dir = make_test_dir()
        try:
            service = TaskService(JSONFileTaskStore(temp_dir / "tasks.json"))

            task = service.create_task("Write docs", "Add getting started guide")

            self.assertEqual(task["id"], 1)
            self.assertEqual(task["title"], "Write docs")
            self.assertFalse(task["completed"])
            self.assertEqual(len(service.list_tasks()), 1)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_task_rejects_blank_title(self):
        temp_dir = make_test_dir()
        try:
            service = TaskService(JSONFileTaskStore(temp_dir / "tasks.json"))

            with self.assertRaises(ValueError):
                service.create_task("   ")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_task_changes_fields(self):
        temp_dir = make_test_dir()
        try:
            service = TaskService(JSONFileTaskStore(temp_dir / "tasks.json"))
            created = service.create_task("Write docs")

            updated = service.update_task(
                created["id"],
                {"description": "API walkthrough", "completed": True},
            )

            self.assertEqual(updated["description"], "API walkthrough")
            self.assertTrue(updated["completed"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_task_removes_existing_task(self):
        temp_dir = make_test_dir()
        try:
            service = TaskService(JSONFileTaskStore(temp_dir / "tasks.json"))
            created = service.create_task("Ship v1")

            deleted = service.delete_task(created["id"])

            self.assertTrue(deleted)
            self.assertEqual(service.list_tasks(), [])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
