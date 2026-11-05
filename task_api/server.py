import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from task_api.service import TaskService
from task_api.storage import JSONFileTaskStore


DEFAULT_DATA_FILE = Path("data") / "tasks.json"


def build_parser():
    parser = argparse.ArgumentParser(description="Task API backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--data-file", default=str(DEFAULT_DATA_FILE))
    return parser


def make_handler(service):
    class TaskAPIHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self._parsed_path()

            if path == "/health":
                self._send_json(200, {"status": "ok"})
                return

            if path == "/tasks":
                self._send_json(200, {"tasks": service.list_tasks()})
                return

            task_id = self._task_id_from_path(path)
            if task_id is None:
                self._send_json(404, {"error": "Not found"})
                return

            task = service.get_task(task_id)
            if task is None:
                self._send_json(404, {"error": "Task not found"})
                return

            self._send_json(200, task)

        def do_POST(self):
            if self._parsed_path() != "/tasks":
                self._send_json(404, {"error": "Not found"})
                return

            payload = self._read_json()
            if payload is None:
                return

            try:
                task = service.create_task(
                    title=str(payload.get("title", "")),
                    description=str(payload.get("description", "")),
                )
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return

            self._send_json(201, task)

        def do_PATCH(self):
            task_id = self._task_id_from_path(self._parsed_path())
            if task_id is None:
                self._send_json(404, {"error": "Not found"})
                return

            payload = self._read_json()
            if payload is None:
                return

            allowed = {"title", "description", "completed"}
            updates = {key: value for key, value in payload.items() if key in allowed}

            try:
                task = service.update_task(task_id, updates)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return

            if task is None:
                self._send_json(404, {"error": "Task not found"})
                return

            self._send_json(200, task)

        def do_DELETE(self):
            task_id = self._task_id_from_path(self._parsed_path())
            if task_id is None:
                self._send_json(404, {"error": "Not found"})
                return

            deleted = service.delete_task(task_id)
            if not deleted:
                self._send_json(404, {"error": "Task not found"})
                return

            self._send_json(200, {"deleted": True})

        def log_message(self, format, *args):
            return

        def _parsed_path(self):
            return urlparse(self.path).path

        def _task_id_from_path(self, path):
            parts = [part for part in path.strip("/").split("/") if part]
            if len(parts) != 2 or parts[0] != "tasks":
                return None
            try:
                return int(parts[1])
            except ValueError:
                return None

        def _read_json(self):
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(400, {"error": "Invalid Content-Length"})
                return None

            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            try:
                return json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Request body must be valid JSON"})
                return None

        def _send_json(self, status_code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return TaskAPIHandler


def create_server(host="127.0.0.1", port=8000, data_file=DEFAULT_DATA_FILE):
    service = TaskService(JSONFileTaskStore(data_file))
    handler = make_handler(service)
    return ThreadingHTTPServer((host, port), handler)


def main(argv=None):
    args = build_parser().parse_args(argv)
    server = create_server(args.host, args.port, args.data_file)
    print(f"Task API running on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
