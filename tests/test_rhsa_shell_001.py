from __future__ import annotations

import tempfile
import tarfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet
from tests.lab_test_utils import add_dir, add_file, load_grade

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "01-shell-basics" / "RHSA-SHELL-001"
TOKEN = "abc123def456"


def make_snapshot(path: Path, complete: bool):
    src = f"/workspace/source_{TOKEN}"
    dst = f"/workspace/destination_{TOKEN}"
    expected = {
        "text": [f"report_{TOKEN}.txt", f"notes_{TOKEN}.txt"],
        "logs": [f"server_{TOKEN}.log", f"audit_{TOKEN}.log"],
        "other": [f"payload_{TOKEN}.bin", f"config_{TOKEN}.conf", f".environment_{TOKEN}"],
    }
    with tarfile.open(path, "w") as tar:
        add_dir(tar, src)
        add_dir(tar, f"{src}/leave_this_directory")
        for cat in expected:
            add_dir(tar, f"{dst}/{cat}")
        for cat, names in expected.items():
            for name in names:
                target = f"{dst}/{cat}/{name}" if complete or name != f".environment_{TOKEN}" else f"{src}/{name}"
                add_file(tar, target, name)


class FileOrganizerTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load((LAB_DIR / "lab.yaml").read_text())
        self.context = {
            "syntax_ok": True,
            "variables": {"TEST_TOKEN": TOKEN},
            "first_run": {"returncode": 0, "timed_out": False},
            "second_run": {"returncode": 0, "timed_out": False},
        }

    def test_complete_state_scores_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, True); make_snapshot(b, True)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            self.assertEqual(result["score"], 100)

    def test_hidden_file_left_behind_loses_other_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, False); make_snapshot(b, False)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            by_id = {x["id"]: x for x in result["tests"]}
            self.assertFalse(by_id["other_files"]["passed"])
            self.assertFalse(by_id["idempotency"]["passed"])


if __name__ == "__main__":
    unittest.main()
