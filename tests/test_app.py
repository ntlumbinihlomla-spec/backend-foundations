import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from calculator import app


class TestAppCli(unittest.TestCase):
    def test_main_requires_a_command(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as exc_info:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                app.main([])

        self.assertEqual(exc_info.exception.code, 2)
        self.assertIn("usage:", stderr.getvalue())

    def test_json_requires_an_action(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as exc_info:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                app.main(["json"])

        self.assertEqual(exc_info.exception.code, 2)
        self.assertIn("usage:", stderr.getvalue())

    def test_finance_summary_writes_requested_report(self):
        report_path = Path("test_report_output.txt")
        stdout = io.StringIO()

        try:
            with patch.object(
                app,
                "summarize_csv_column",
                return_value={
                    "rows": 3,
                    "sum": 30.0,
                    "average": 10.0,
                    "min": 5.0,
                    "max": 15.0,
                },
            ):
                with redirect_stdout(stdout):
                    app.main(
                        [
                            "finance",
                            "summary",
                            "sales.csv",
                            "amount",
                            "--out",
                            str(report_path),
                        ]
                    )

            self.assertIn("SALES SUMMARY REPORT", stdout.getvalue())
            self.assertIn(f"Report saved to {report_path}", stdout.getvalue())
            self.assertIn(
                "Total Revenue: R30.00",
                report_path.read_text(encoding="utf-8"),
            )
        finally:
            if report_path.exists():
                report_path.unlink()

    def test_finance_batch_uses_ascii_output(self):
        stdout = io.StringIO()

        with patch.object(
            app,
            "batch_summarize",
            return_value=([("sales.csv", 12.5), ("more.csv", 7.5)], 20.0),
        ):
            with redirect_stdout(stdout):
                app.main(["finance", "batch", "reports", "amount"])

        output = stdout.getvalue()
        self.assertIn("sales.csv -> R12.50", output)
        self.assertIn("TOTAL ACROSS FILES -> R20.00", output)

    def test_report_audit_writes_requested_report(self):
        report_path = Path("audit_report_output.txt")
        stdout = io.StringIO()

        try:
            with patch.object(
                app,
                "build_workspace_audit",
                return_value={
                    "folder": "examples",
                    "total_files": 2,
                    "total_lines": 8,
                    "csv_files": [{"name": "sales.csv", "rows": 3, "columns": 2}],
                    "json_files": [],
                    "log_files": [{"name": "app.log", "errors": 1}],
                },
            ):
                with redirect_stdout(stdout):
                    app.main(
                        [
                            "report",
                            "audit",
                            "examples",
                            "--out",
                            str(report_path),
                        ]
                    )

            self.assertIn("WORKSPACE AUDIT REPORT", stdout.getvalue())
            self.assertIn(f"Report saved to {report_path}", stdout.getvalue())
            self.assertIn(
                "Total Files : 2",
                report_path.read_text(encoding="utf-8"),
            )
        finally:
            if report_path.exists():
                report_path.unlink()


if __name__ == "__main__":
    unittest.main()
