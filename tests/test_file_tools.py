import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from calculator.file_tools import count_lines, count_lines_in_dir, count_words


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestFileTools(unittest.TestCase):
    def test_count_lines_counts_all_lines(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sample.txt"
            sample.write_text("one\ntwo\nthree\n", encoding="utf-8")

            self.assertEqual(count_lines(sample), 3)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_words_counts_split_words(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sample.txt"
            sample.write_text("one two\nthree", encoding="utf-8")

            self.assertEqual(count_words(sample), 3)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_lines_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            count_lines("missing.txt")

    def test_count_lines_in_dir_sums_multiple_files(self):
        temp_path = make_test_dir()
        try:
            (temp_path / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
            (temp_path / "b.txt").write_text("three\n", encoding="utf-8")
            nested = temp_path / "notes"
            nested.mkdir()
            (nested / "nested.txt").write_text("four\nfive\n", encoding="utf-8")
            (nested / "binary.dat").write_bytes(b"\xff\xfe\x00")

            self.assertEqual(count_lines_in_dir(temp_path), 5)
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

    def test_count_lines_in_dir_raises_for_missing_folder(self):
        with self.assertRaises(NotADirectoryError):
            count_lines_in_dir("missing-folder")


if __name__ == "__main__":
    unittest.main()
