from __future__ import annotations

import tempfile
import tarfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet
from tests.lab_test_utils import add_file, load_grade

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "04-text-processing" / "RHSA-TEXT-001"
VARS = {
    "TEST_TOKEN": "abc123def456",
    "IP_A": "203.0.113.21", "IP_B": "203.0.113.91", "IP_C": "203.0.113.181",
    "COUNT_A": "8", "COUNT_B": "5", "COUNT_C": "2",
}


def make_snapshot(path: Path, text: str):
    with tarfile.open(path, "w") as tar:
        add_file(tar, f"/workspace/failed_logins_{VARS['TEST_TOKEN']}.txt", text)


class TextAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load((LAB_DIR / "lab.yaml").read_text())
        self.context = {
            "syntax_ok": True, "variables": VARS,
            "first_run": {"returncode": 0, "timed_out": False},
            "second_run": {"returncode": 0, "timed_out": False},
        }
        self.correct = "8 203.0.113.21\n5 203.0.113.91\n2 203.0.113.181\n"

    def test_correct_report_scores_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, self.correct); make_snapshot(b, self.correct)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            self.assertEqual(result["score"], 100)

    def test_wrong_count_loses_count_and_order_points(self):
        wrong = "8 203.0.113.21\n99 203.0.113.91\n2 203.0.113.181\n"
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, wrong); make_snapshot(b, wrong)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            by_id = {x["id"]: x for x in result["tests"]}
            self.assertLess(by_id["counts"]["points"], by_id["counts"]["max_points"])
            self.assertFalse(by_id["descending_order"]["passed"])


if __name__ == "__main__":
    unittest.main()
