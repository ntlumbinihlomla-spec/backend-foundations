import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from calculator.report_tools import build_workspace_audit, format_workspace_audit


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestReportTools(unittest.TestCase):
    def test_build_workspace_audit_summarizes_supported_files(self):
        temp_dir = make_test_dir()
        try:
            (temp_dir / "notes.txt").write_text("one\ntwo\n", encoding="utf-8")
            (temp_dir / "sales.csv").write_text(
                "amount,name\n10,A\n20,B\n",
                encoding="utf-8",
            )
            (temp_dir / "sample.json").write_text(
                json.dumps({"name": "Ada", "role": "Engineer"}),
                encoding="utf-8",
            )
            (temp_dir / "app.log").write_text(
                "INFO started\nERROR failed\nerror retry\n",
                encoding="utf-8",
            )

            report = build_workspace_audit(temp_dir)

            self.assertEqual(report["total_files"], 4)
            self.assertEqual(report["total_lines"], 9)
            self.assertEqual(report["csv_files"][0]["rows"], 3)
            self.assertEqual(report["csv_files"][0]["columns"], 2)
            self.assertEqual(report["json_files"][0]["keys"], 2)
            self.assertEqual(report["log_files"][0]["errors"], 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_build_workspace_audit_raises_for_missing_folder(self):
        with self.assertRaises(NotADirectoryError):
            build_workspace_audit("missing-folder")

    def test_format_workspace_audit_renders_sections(self):
        output = format_workspace_audit(
            {
                "folder": "examples",
                "total_files": 3,
                "total_lines": 9,
                "csv_files": [{"name": "sales.csv", "rows": 3, "columns": 2}],
                "json_files": [{"name": "sample.json", "keys": 2}],
                "log_files": [{"name": "app.log", "errors": 1}],
            }
        )

        self.assertIn("WORKSPACE AUDIT REPORT", output)
        self.assertIn("- sales.csv: rows=3, columns=2", output)
        self.assertIn("- sample.json: top-level keys=2", output)
        self.assertIn("- app.log: errors=1", output)


if __name__ == "__main__":
    unittest.main()
