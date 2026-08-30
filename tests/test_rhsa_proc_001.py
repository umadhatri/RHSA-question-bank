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
LAB_DIR = (
    ROOT
    / "labs"
    / "07-process-management"
    / "RHSA-PROC-001"
)

RUNAWAY_PID = 34
WORKER_PID = 35
CONTROL_PID = 36


def add_file(
    tar: tarfile.TarFile,
    name: str,
    content: str,
):
    data = content.encode()

    info = tarfile.TarInfo(name.lstrip("/"))
    info.size = len(data)
    info.mode = 0o644

    tar.addfile(info, io.BytesIO(data))


def snapshot(
    path: Path,
    *,
    runaway: str = "",
    worker: str = f"{WORKER_PID} S 10\n",
    control: str = f"{CONTROL_PID} S 0\n",
):
    with tarfile.open(path, "w") as tar:
        add_file(
            tar,
            "/run/cyberrange-runaway-state",
            runaway,
        )

        add_file(
            tar,
            "/run/cyberrange-worker-state",
            worker,
        )

        add_file(
            tar,
            "/run/cyberrange-control-state",
            control,
        )


def grader_fn():
    path = LAB_DIR / "grader.py"

    spec = importlib.util.spec_from_file_location(
        "rhsa_proc_001_test",
        path,
    )

    module = importlib.util.module_from_spec(spec)

    assert spec and spec.loader
    spec.loader.exec_module(module)

    return module.grade


def criterion(
    result: dict,
    criterion_id: str,
) -> dict:
    return next(
        item
        for item in result["tests"]
        if item["id"] == criterion_id
    )


class ProcessManagementGraderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text()
        )

        self.context = {
            "syntax_ok": True,
            "setup": {
                "stdout": "\n".join(
                    [
                        f"RUNAWAY_PID={RUNAWAY_PID}",
                        f"WORKER_PID={WORKER_PID}",
                        f"CONTROL_PID={CONTROL_PID}",
                    ]
                )
            },
            "first_run": {
                "returncode": 0,
                "timed_out": False,
            },
            "second_run": {
                "returncode": 0,
                "timed_out": False,
            },
        }

    def grade_snapshots(
        self,
        first_options: dict | None = None,
        second_options: dict | None = None,
    ):
        first_options = first_options or {}

        second_options = (
            first_options
            if second_options is None
            else second_options
        )

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"

            snapshot(first, **first_options)
            snapshot(second, **second_options)

            with SnapshotSet(
                {
                    "after_first": str(first),
                    "after_second": str(second),
                }
            ) as snaps:
                return grader_fn()(
                    self.lab,
                    self.context,
                    snaps,
                )

    def test_correct_process_state_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_replacement_worker_is_rejected(self):
        result = self.grade_snapshots(
            {
                "worker": "99 S 10\n",
            }
        )

        self.assertFalse(
            criterion(
                result,
                "worker_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "worker_priority",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

        self.assertLess(
            result["score"],
            int(self.lab["grading"]["pass_score"]),
        )

    def test_killing_control_process_is_rejected(self):
        result = self.grade_snapshots(
            {
                "control": "",
            }
        )

        self.assertFalse(
            criterion(
                result,
                "control_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "control_priority",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "no_extra_processes",
            )["passed"]
        )

    def test_wrong_worker_priority_is_rejected(self):
        result = self.grade_snapshots(
            {
                "worker": f"{WORKER_PID} S 0\n",
            }
        )

        self.assertTrue(
            criterion(
                result,
                "worker_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "worker_priority",
            )["passed"]
        )

    def test_additional_worker_is_rejected(self):
        result = self.grade_snapshots(
            {
                "worker": (
                    f"{WORKER_PID} S 10\n"
                    "99 S 10\n"
                ),
            }
        )

        self.assertTrue(
            criterion(
                result,
                "worker_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "no_extra_processes",
            )["passed"]
        )

    def test_second_run_must_preserve_process_state(self):
        result = self.grade_snapshots(
            {},
            {
                "control": "",
            },
        )

        self.assertTrue(
            criterion(
                result,
                "control_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

    def test_zombie_runaway_counts_as_terminated(self):
        result = self.grade_snapshots(
            {
                "runaway": f"{RUNAWAY_PID} Z 0\n",
            }
        )

        self.assertTrue(
            criterion(
                result,
                "runaway_terminated",
            )["passed"]
        )

        self.assertEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()
