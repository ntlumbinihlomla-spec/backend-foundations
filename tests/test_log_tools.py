import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from calculator.log_tools import count_errors


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestLogTools(unittest.TestCase):
    def test_count_errors_is_case_insensitive(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "app.log"
            sample.write_text(
                "INFO startup\nERROR failed\nwarning\nerror retry\n",
                encoding="utf-8",
            )

            self.assertEqual(count_errors(sample), 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_errors_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            count_errors("missing.log")


if __name__ == "__main__":
    unittest.main()
