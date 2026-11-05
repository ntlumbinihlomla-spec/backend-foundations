import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from calculator.json_tools import count_keys, pretty_print_json


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestJsonTools(unittest.TestCase):
    def test_pretty_print_json_formats_output(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sample.json"
            sample.write_text(json.dumps({"name": "Ada", "age": 30}), encoding="utf-8")

            output = pretty_print_json(sample)

            self.assertIn('\n    "name": "Ada"', output)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_keys_counts_top_level_dict_keys(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sample.json"
            sample.write_text(json.dumps({"name": "Ada", "age": 30}), encoding="utf-8")

            self.assertEqual(count_keys(sample), 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_count_keys_returns_zero_for_json_array(self):
        temp_dir = make_test_dir()
        try:
            sample = temp_dir / "sample.json"
            sample.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

            self.assertEqual(count_keys(sample), 0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pretty_print_json_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            pretty_print_json("missing.json")


if __name__ == "__main__":
    unittest.main()
