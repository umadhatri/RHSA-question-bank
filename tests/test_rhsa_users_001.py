from __future__ import annotations

import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "03-users-groups" / "RHSA-USERS-001"


def add_file(tar: tarfile.TarFile, name: str, content: str):
    data = content.encode()
    info = tarfile.TarInfo(name.lstrip("/"))
    info.size = len(data)
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar: tarfile.TarFile, name: str, mode: int, gid: int):
    info = tarfile.TarInfo(name.lstrip("/").rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = 0
    info.gid = gid
    tar.addfile(info)


def snapshot(path: Path, complete: bool):
    username = "student_123456"
    groupname = "team_654321"
    gid = 2200
    with tarfile.open(path, "w") as tar:
        add_file(tar, "/etc/passwd", f"root:x:0:0:root:/root:/bin/bash\n{username}:x:2000:2000::/home/{username}:/bin/bash\n")
        add_file(tar, "/etc/group", f"root:x:0:\n{groupname}:x:{gid}:{username if complete else ''}\n")
        add_dir(tar, f"/srv/{groupname}", 0o2770 if complete else 0o755, gid if complete else 0)


def grader_fn():
    path = LAB_DIR / "grader.py"
    spec = importlib.util.spec_from_file_location("rhsa_users_001_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.grade


class UserProvisioningGraderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load((LAB_DIR / "lab.yaml").read_text())
        self.context = {
            "syntax_ok": True,
            "variables": {"TEST_USERNAME": "student_123456", "TEST_GROUP": "team_654321"},
            "first_run": {"returncode": 0, "timed_out": False},
            "second_run": {"returncode": 0, "timed_out": False},
        }

    def test_complete_state_twice_scores_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"
            snapshot(first, True)
            snapshot(second, True)
            with SnapshotSet({"after_first": str(first), "after_second": str(second)}) as snaps:
                result = grader_fn()(self.lab, self.context, snaps)
            self.assertEqual(result["score"], 100)

    def test_incomplete_state_cannot_receive_idempotency_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"
            snapshot(first, False)
            snapshot(second, False)
            with SnapshotSet({"after_first": str(first), "after_second": str(second)}) as snaps:
                result = grader_fn()(self.lab, self.context, snaps)
            criterion = next(x for x in result["tests"] if x["id"] == "idempotency")
            self.assertFalse(criterion["passed"])
            self.assertEqual(criterion["points"], 0)

    def test_second_run_must_preserve_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"
            snapshot(first, True)
            snapshot(second, False)
            with SnapshotSet({"after_first": str(first), "after_second": str(second)}) as snaps:
                result = grader_fn()(self.lab, self.context, snaps)
            criterion = next(x for x in result["tests"] if x["id"] == "idempotency")
            self.assertFalse(criterion["passed"])


if __name__ == "__main__":
    unittest.main()
