import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from calculator.csv_tools import count_columns, count_rows


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestCsvTools(unittest.TestCase):
    def test_count_rows_counts_header_and_data_rows(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("amount,name\n10,A\n20,B\n", encoding="utf-8")

            self.assertEqual(count_rows(sample), 3)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_columns_reads_header_width(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sales.csv"
            sample.write_text("amount,name,status\n10,A,paid\n", encoding="utf-8")

            self.assertEqual(count_columns(sample), 3)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_columns_raises_for_empty_file(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "empty.csv"
            sample.write_text("", encoding="utf-8")

            with self.assertRaises(ValueError):
                count_columns(sample)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_rows_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            count_rows("missing.csv")


if __name__ == "__main__":
    unittest.main()
