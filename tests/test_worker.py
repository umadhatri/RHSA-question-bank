from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from worker.run_job import WorkerError, resolve_lab

ROOT = Path(__file__).resolve().parents[1]


class GradingWorkerTests(unittest.TestCase):
    def test_resolves_existing_lab_by_declared_id(self):
        lab = resolve_lab(ROOT, "RHSA-USERS-001")
        self.assertEqual(lab.name, "RHSA-USERS-001")
        self.assertEqual(lab.parent.name, "03-users-groups")

    def test_rejects_unknown_lab_id(self):
        with self.assertRaises(WorkerError):
            resolve_lab(ROOT, "RHSA-NOT-REAL-999")

    def test_rejects_duplicate_lab_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for module in ("01-old", "02-current"):
                lab = root / "labs" / module / "RHSA-DUP-001"
                lab.mkdir(parents=True)
                (lab / "lab.yaml").write_text(
                    "id: RHSA-DUP-001\ntitle: Duplicate\n", encoding="utf-8"
                )
            with self.assertRaises(WorkerError):
                resolve_lab(root, "RHSA-DUP-001")


if __name__ == "__main__":
    unittest.main()
