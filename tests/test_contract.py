from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet
from grader.validation import validate_grader_signature, validate_lab_config

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "01-users-groups" / "RHSA-USERS-001"


def add_file(tar: tarfile.TarFile, name: str, content: str, mode: int = 0o644, uid: int = 0, gid: int = 0):
    data = content.encode()
    info = tarfile.TarInfo(name.lstrip("/"))
    info.size = len(data)
    info.mode = mode
    info.uid = uid
    info.gid = gid
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar: tarfile.TarFile, name: str, mode: int, uid: int, gid: int):
    info = tarfile.TarInfo(name.lstrip("/").rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = uid
    info.gid = gid
    tar.addfile(info)


def make_snapshot(path: Path, *, correct: bool):
    username = "student_123456"
    groupname = "team_654321"
    group_gid = 2200
    with tarfile.open(path, "w") as tar:
        add_file(
            tar,
            "/etc/passwd",
            f"root:x:0:0:root:/root:/bin/bash\n{username}:x:2000:2000::/home/{username}:/bin/bash\n",
        )
        members = username if correct else ""
        add_file(
            tar,
            "/etc/group",
            f"root:x:0:\n{groupname}:x:{group_gid}:{members}\n",
        )
        add_dir(
            tar,
            f"/srv/{groupname}",
            0o2770 if correct else 0o755,
            0,
            group_gid if correct else 0,
        )


class ContractTests(unittest.TestCase):
    def test_lab_schema_and_rubric(self):
        lab = yaml.safe_load((LAB_DIR / "lab.yaml").read_text())
        validate_lab_config(lab, ROOT / "schemas" / "lab.schema.json")
        self.assertEqual(sum(c["points"] for c in lab["grading"]["criteria"]), 100)

    def test_rootfs_snapshot_reads_linux_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rootfs.tar"
            make_snapshot(path, correct=True)
            with RootfsSnapshot(str(path)) as snap:
                self.assertEqual(snap.user("student_123456").shell, "/bin/bash")
                self.assertIn("student_123456", snap.group("team_654321").members)
                self.assertEqual(snap.mode("/srv/team_654321"), 0o2770)
                self.assertEqual(snap.gid("/srv/team_654321"), 2200)

    def test_result_schema_accepts_minimal_result(self):
        schema = json.loads((ROOT / "schemas" / "result.schema.json").read_text())
        result = {
            "contract_version": 1,
            "runner_version": "0.2.0",
            "lab_id": "RHSA-USERS-001",
            "title": "User and Group Provisioning",
            "lab_version": 1,
            "score": 100,
            "max_score": 100,
            "pass_score": 70,
            "passed": True,
            "tests": [],
            "metadata": {
                "seed": 1,
                "variables": {},
                "image": "example:1",
                "submission_filename": "answer.sh",
                "submission_sha256": "x",
                "lab_package_sha256": "y",
                "first_run": {},
                "second_run": {}
            }
        }
        Draft202012Validator(schema).validate(result)

    def test_gradebook_preserves_rubric_order(self):
        lab = {"grading": {"criteria": [{"id": "a", "points": 2}, {"id": "b", "points": 3}]}}
        book = GradeBook(lab)
        book.check("b", True, "ok", "bad")
        book.check("a", False, "ok", "bad")
        result = book.finalize()
        self.assertEqual([x["id"] for x in result["tests"]], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
