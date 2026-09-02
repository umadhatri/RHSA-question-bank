from __future__ import annotations

import tempfile
import tarfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet
from tests.lab_test_utils import add_dir, add_file, load_grade


ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = (
    ROOT
    / "labs"
    / "11-unix-programming-environment"
    / "TUPE-C03-004"
)

TOKEN = "abc123def456"
COUNT_A = 5
COUNT_B = 11

VARIABLES = {
    "TEST_TOKEN": TOKEN,
    "COUNT_A": COUNT_A,
    "COUNT_B": COUNT_B,
}

BIN_DIR = f"/workspace/student_bin_{TOKEN}"
COMMAND = f"{BIN_DIR}/recordcount"
INPUT_A = f"/workspace/data_a_{TOKEN}.txt"
INPUT_B = f"/workspace/data_b_{TOKEN}.txt"
PROBE = f"/workspace/command_probe_{TOKEN}.txt"
RESOLVED = f"/workspace/resolved_command_{TOKEN}.txt"


def expected_input(prefix: str, count: int) -> str:
    return "".join(
        f"{prefix}-{TOKEN}-{index:02d}\n"
        for index in range(1, count + 1)
    )


def make_snapshot(
    path: Path,
    *,
    command_exists: bool = True,
    command_mode: int = 0o755,
    command_content: str = "#!/usr/bin/env bash\necho test\n",
    resolved_path: str | None = None,
    probe_text: str | None = None,
    input_a: str | None = None,
    input_b: str | None = None,
) -> None:
    resolved_path = COMMAND if resolved_path is None else resolved_path
    probe_text = (
        f"A={COUNT_A}\nB={COUNT_B}\n"
        if probe_text is None
        else probe_text
    )
    input_a = (
        expected_input("alpha", COUNT_A)
        if input_a is None
        else input_a
    )
    input_b = (
        expected_input("beta", COUNT_B)
        if input_b is None
        else input_b
    )

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        add_dir(tar, BIN_DIR)

        if command_exists:
            add_file(
                tar,
                COMMAND,
                command_content,
                mode=command_mode,
            )

        add_file(tar, INPUT_A, input_a)
        add_file(tar, INPUT_B, input_b)
        add_file(tar, PROBE, probe_text)
        add_file(tar, RESOLVED, resolved_path + "\n")


class PersonalCommandInstallerTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text(encoding="utf-8")
        )

        self.context = {
            "syntax_ok": True,
            "variables": dict(VARIABLES),
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
        first_kwargs: dict | None = None,
        second_kwargs: dict | None = None,
    ) -> dict:
        first_kwargs = first_kwargs or {}
        second_kwargs = second_kwargs or {}

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"

            make_snapshot(first, **first_kwargs)
            make_snapshot(second, **second_kwargs)

            with SnapshotSet(
                {
                    "after_first": str(first),
                    "after_second": str(second),
                }
            ) as snapshots:
                return load_grade(LAB_DIR / "grader.py")(
                    self.lab,
                    self.context,
                    snapshots,
                )

    def test_complete_state_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_missing_command_loses_creation_and_execution_points(self):
        result = self.grade_snapshots(
            {
                "command_exists": False,
                "resolved_path": "/usr/local/bin/recordcount",
                "probe_text": "A=9999\nB=9999\n",
            },
            {
                "command_exists": False,
                "resolved_path": "/usr/local/bin/recordcount",
                "probe_text": "A=9999\nB=9999\n",
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["command_created"]["passed"])
        self.assertFalse(by_id["command_executable"]["passed"])
        self.assertFalse(by_id["path_resolution"]["passed"])
        self.assertFalse(by_id["argument_behavior"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_non_executable_command_is_rejected(self):
        result = self.grade_snapshots(
            {"command_mode": 0o644},
            {"command_mode": 0o644},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["command_created"]["passed"])
        self.assertFalse(by_id["command_executable"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_wrong_path_resolution_is_rejected(self):
        result = self.grade_snapshots(
            {"resolved_path": "/usr/local/bin/recordcount"},
            {"resolved_path": "/usr/local/bin/recordcount"},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["path_resolution"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_wrong_argument_results_are_rejected(self):
        result = self.grade_snapshots(
            {"probe_text": "A=9999\nB=9999\n"},
            {"probe_text": "A=9999\nB=9999\n"},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["argument_behavior"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_modified_input_is_rejected(self):
        result = self.grade_snapshots(
            {"input_a": "modified\n"},
            {"input_a": "modified\n"},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["input_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_second_installation_change_loses_only_idempotency(self):
        first_content = "#!/usr/bin/env bash\nawk 'END { print NR }' \"$1\"\n"
        second_content = "#!/usr/bin/env bash\nwc -l < \"$1\"\n"

        result = self.grade_snapshots(
            {"command_content": first_content},
            {"command_content": second_content},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["command_created"]["passed"])
        self.assertTrue(by_id["command_executable"]["passed"])
        self.assertTrue(by_id["path_resolution"]["passed"])
        self.assertTrue(by_id["argument_behavior"]["passed"])
        self.assertTrue(by_id["input_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 85)


if __name__ == "__main__":
    unittest.main()
