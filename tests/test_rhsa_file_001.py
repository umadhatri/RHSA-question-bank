from __future__ import annotations

import tempfile
import tarfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet
from tests.lab_test_utils import add_dir, add_file, load_grade

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "02-files-permissions" / "RHSA-FILE-001"
TOKEN = "abc123def456"
GID = 2400


def make_snapshot(path: Path, correct: bool):
    project = f"/srv/project_{TOKEN}"
    with tarfile.open(path, "w") as tar:
        add_file(tar, "/etc/group", f"root:x:0:\nproj_{TOKEN}:x:{GID}:\n")
        add_dir(tar, project, 0o2770 if correct else 0o755, gid=GID if correct else 0)
        content = f"Existing project notes for {TOKEN}. Do not overwrite.\n" if correct else "overwritten\n"
        add_file(tar, f"{project}/README.txt", content, 0o660 if correct else 0o644, gid=GID if correct else 0)
        add_dir(tar, f"{project}/archive", 0o2750 if correct else 0o755, gid=GID if correct else 0)


class SecureProjectTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load((LAB_DIR / "lab.yaml").read_text())
        self.context = {
            "syntax_ok": True,
            "variables": {"TEST_TOKEN": TOKEN, "README_PRESENT": "1"},
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


    def test_missing_readme_case_accepts_newly_created_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, True); make_snapshot(b, True)
            context = dict(self.context)
            context["variables"] = {"TEST_TOKEN": TOKEN, "README_PRESENT": "0"}
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, context, snaps)
            self.assertEqual(result["score"], 100)

    def test_overwritten_readme_fails_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, False); make_snapshot(b, False)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            by_id = {x["id"]: x for x in result["tests"]}
            self.assertFalse(by_id["readme_integrity"]["passed"])
            self.assertFalse(by_id["idempotency"]["passed"])


if __name__ == "__main__":
    unittest.main()
