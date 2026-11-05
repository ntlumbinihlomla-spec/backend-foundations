import json
import shutil
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from task_api.server import create_server


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestTaskAPIServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = make_test_dir()
        self.server = create_server("127.0.0.1", 0, self.temp_dir / "tasks.json")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_endpoint(self):
        status, payload = self.request_json("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_create_and_list_tasks(self):
        created_status, created = self.request_json(
            "POST",
            "/tasks",
            {"title": "Build API", "description": "Implement CRUD endpoints"},
        )
        list_status, listing = self.request_json("GET", "/tasks")

        self.assertEqual(created_status, 201)
        self.assertEqual(created["title"], "Build API")
        self.assertEqual(list_status, 200)
        self.assertEqual(len(listing["tasks"]), 1)

    def test_patch_and_delete_task(self):
        _, created = self.request_json("POST", "/tasks", {"title": "Refine tests"})

        patch_status, patched = self.request_json(
            "PATCH",
            f"/tasks/{created['id']}",
            {"completed": True},
        )
        delete_status, deleted = self.request_json("DELETE", f"/tasks/{created['id']}")

        self.assertEqual(patch_status, 200)
        self.assertTrue(patched["completed"])
        self.assertEqual(delete_status, 200)
        self.assertTrue(deleted["deleted"])

    def test_create_task_requires_title(self):
        status, payload = self.request_json("POST", "/tasks", {"title": "   "})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def request_json(self, method, path, payload=None):
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))
