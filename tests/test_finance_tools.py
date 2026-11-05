import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from calculator.finance_tools import batch_summarize, get_csv_columns, summarize_csv_column


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestFinanceTools(unittest.TestCase):
    def test_summarize_csv_column_returns_basic_stats(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("amount\n10\n20\n30\n", encoding="utf-8")

            summary = summarize_csv_column(sample, "amount")

            self.assertEqual(summary["rows"], 3)
            self.assertEqual(summary["sum"], 60.0)
            self.assertEqual(summary["average"], 20.0)
            self.assertEqual(summary["min"], 10.0)
            self.assertEqual(summary["max"], 30.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summarize_csv_column_skips_non_numeric_values(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("amount\n10\ninvalid\n30\n", encoding="utf-8")

            summary = summarize_csv_column(sample, "amount")

            self.assertEqual(summary["rows"], 2)
            self.assertEqual(summary["sum"], 40.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summarize_csv_column_raises_for_missing_column(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("price\n10\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                summarize_csv_column(sample, "amount")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summarize_csv_column_raises_when_no_numeric_data_exists(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("amount\ninvalid\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                summarize_csv_column(sample, "amount")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_csv_columns_returns_headers(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("client,amount,region\nAcme,10,West\n", encoding="utf-8")

            self.assertEqual(get_csv_columns(sample), ["client", "amount", "region"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_batch_summarize_adds_totals_across_csv_files(self):
        temp_path = make_test_dir()
        try:
            (temp_path / "sales_a.csv").write_text("amount\n10\n20\n", encoding="utf-8")
            (temp_path / "sales_b.csv").write_text("amount\n5\n", encoding="utf-8")
            (temp_path / "notes.txt").write_text("skip me", encoding="utf-8")

            results, grand_total = batch_summarize(temp_path, "amount")

            self.assertEqual(dict(results), {"sales_a.csv": 30.0, "sales_b.csv": 5.0})
            self.assertEqual(grand_total, 35.0)
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def test_batch_summarize_raises_for_missing_folder(self):
        with self.assertRaises(NotADirectoryError):
            batch_summarize("missing-folder", "amount")


if __name__ == "__main__":
    unittest.main()
