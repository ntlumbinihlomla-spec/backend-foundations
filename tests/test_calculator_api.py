import asyncio
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from starlette.datastructures import UploadFile

from calculator import api


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestCalculatorApi(unittest.TestCase):
    def setUp(self):
        self.original_upload_folder = api.UPLOAD_FOLDER
        self.temp_dir = make_test_dir()
        self.upload_dir = self.temp_dir / "uploads"
        self.upload_dir.mkdir()
        api.UPLOAD_FOLDER = self.upload_dir

    def tearDown(self):
        api.UPLOAD_FOLDER = self.original_upload_folder
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_returns_ok(self):
        self.assertEqual(api.health(), {"status": "ok"})

    def test_summary_returns_error_for_missing_file(self):
        response = api.get_summary("missing.csv", "amount")
        self.assertEqual(response, {"error": "File not found"})

    def test_summary_returns_stats_for_uploaded_file(self):
        sample = self.upload_dir / "sales.csv"
        sample.write_text("amount\n10\n20\n", encoding="utf-8")

        response = api.get_summary("sales.csv", "amount")

        self.assertEqual(response["rows"], 2)
        self.assertEqual(response["sum"], 30.0)
        self.assertEqual(response["average"], 15.0)

    def test_summary_returns_error_for_missing_column(self):
        sample = self.upload_dir / "sales.csv"
        sample.write_text("price\n10\n", encoding="utf-8")

        response = api.get_summary("sales.csv", "amount")

        self.assertEqual(response, {"error": "Column not found in CSV"})

    def test_batch_summary_returns_totals(self):
        batch_dir = self.temp_dir / "batch"
        batch_dir.mkdir()
        (batch_dir / "sales_a.csv").write_text("amount\n10\n20\n", encoding="utf-8")
        (batch_dir / "sales_b.csv").write_text("amount\n5\n", encoding="utf-8")

        response = api.batch_summary(str(batch_dir), "amount")

        self.assertEqual(response["grand_total"], 35.0)
        self.assertEqual(
            response["files"],
            [
                {"file": "sales_a.csv", "total": 30.0},
                {"file": "sales_b.csv", "total": 5.0},
            ],
        )

    def test_batch_summary_returns_error_for_missing_folder(self):
        response = api.batch_summary("missing-folder", "amount")
        self.assertEqual(response, {"error": "Folder not found"})

    def test_upload_file_saves_contents(self):
        upload = UploadFile(
            filename="sales.csv",
            file=(self.temp_dir / "source.csv").open("w+b"),
        )
        upload.file.write(b"amount\n10\n")
        upload.file.seek(0)

        response = asyncio.run(api.upload_file(upload))

        saved = self.upload_dir / "sales.csv"
        self.assertEqual(response["filename"], "sales.csv")
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_text(encoding="utf-8"), "amount\n10\n")
        upload.file.close()


if __name__ == "__main__":
    unittest.main()
