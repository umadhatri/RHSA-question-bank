from __future__ import annotations

import io
import tempfile
import tarfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet
from tests.lab_test_utils import add_dir, add_file, load_grade

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "05-archives-backups" / "RHSA-BACKUP-001"
TOKEN = "abc123def456"


def archive_bytes(extra: bool = False) -> bytes:
    expected = {
        f"README_{TOKEN}.txt": f"Training backup {TOKEN}\n".encode(),
        "configs/app.conf": b"listen_port=8443\nmode=training\n",
        "data/users.csv": b"user,role\nalice,admin\nbob,operator\n",
        "data/nested/state.txt": f"nested={TOKEN}\n".encode(),
        ".backup_meta": f"secret-marker={TOKEN}\n".encode(),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in expected.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
        if extra:
            data = b"unexpected\n"
            info = tarfile.TarInfo("extra.txt"); info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def make_snapshot(path: Path, extra: bool = False, second_extra_backup: bool = False):
    dst = f"/var/backups/training_{TOKEN}"
    with tarfile.open(path, "w") as tar:
        add_dir(tar, dst)
        add_file(tar, f"{dst}/backup_{TOKEN}.tar.gz", archive_bytes(extra))
        if second_extra_backup:
            add_file(tar, f"{dst}/backup-old.tar.gz", archive_bytes(False))


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load((LAB_DIR / "lab.yaml").read_text())
        self.context = {
            "syntax_ok": True,
            "variables": {"TEST_TOKEN": TOKEN},
            "first_run": {"returncode": 0, "timed_out": False},
            "second_run": {"returncode": 0, "timed_out": False},
        }

    def test_correct_archive_scores_100(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a); make_snapshot(b)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            self.assertEqual(result["score"], 100)

    def test_extra_file_and_extra_backup_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            make_snapshot(a, extra=True); make_snapshot(b, extra=True, second_extra_backup=True)
            with SnapshotSet({"after_first": str(a), "after_second": str(b)}) as snaps:
                result = load_grade(LAB_DIR / "grader.py")(self.lab, self.context, snaps)
            by_id = {x["id"]: x for x in result["tests"]}
            self.assertFalse(by_id["no_extra_entries"]["passed"])
            self.assertFalse(by_id["idempotency"]["passed"])


if __name__ == "__main__":
    unittest.main()
