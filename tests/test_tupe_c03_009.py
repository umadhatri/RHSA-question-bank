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
    / "TUPE-C03-009"
)

TOKEN = "abc123def456"
BUILD_A = 317
BUILD_B = 842

VARIABLES = {
    "TEST_TOKEN": TOKEN,
    "BUILD_A": BUILD_A,
    "BUILD_B": BUILD_B,
}

OUTPUT_A = f"/workspace/notice_a_{TOKEN}.txt"
OUTPUT_B = f"/workspace/notice_b_{TOKEN}.txt"

PROJECT_A = f"alpha-{TOKEN} build-{BUILD_A} [release] *"
PROJECT_B = f"beta-{TOKEN} build-{BUILD_B} [release] *"
OWNER_A = f"Owner A {TOKEN} $ops"
OWNER_B = f"Owner B {TOKEN} $ops"


def expected_document(project: str, owner: str) -> str:
    return (
        "BEGIN NOTICE\n"
        f"project={project}\n"
        f"owner={owner}\n"
        "home-literal=$HOME\n"
        "command-literal=$(date)\n"
        "backtick-literal=`whoami`\n"
        "END NOTICE\n"
    )


EXPECTED_A = expected_document(PROJECT_A, OWNER_A)
EXPECTED_B = expected_document(PROJECT_B, OWNER_B)


def make_snapshot(
    path: Path,
    *,
    output_a: str | None = EXPECTED_A,
    output_b: str | None = EXPECTED_B,
) -> None:
    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")

        if output_a is not None:
            add_file(tar, OUTPUT_A, output_a)

        if output_b is not None:
            add_file(tar, OUTPUT_B, output_b)


class HereDocumentGeneratorTests(unittest.TestCase):
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

    def test_missing_second_notice_is_rejected(self):
        result = self.grade_snapshots(
            {"output_b": None},
            {"output_b": None},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["first_document"]["passed"])
        self.assertFalse(by_id["second_document"]["passed"])
        self.assertFalse(by_id["dynamic_fields"]["passed"])
        self.assertFalse(by_id["literal_shell_text"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_expanded_home_is_rejected(self):
        expanded = EXPECTED_A.replace(
            "home-literal=$HOME",
            "home-literal=/root",
        )

        result = self.grade_snapshots(
            {"output_a": expanded},
            {"output_a": expanded},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["first_document"]["passed"])
        self.assertTrue(by_id["dynamic_fields"]["passed"])
        self.assertFalse(by_id["literal_shell_text"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_executed_command_substitution_is_rejected(self):
        expanded = EXPECTED_A.replace(
            "command-literal=$(date)",
            "command-literal=Thu Sep  3 17:30:00 IST 2026",
        )

        result = self.grade_snapshots(
            {"output_a": expanded},
            {"output_a": expanded},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["first_document"]["passed"])
        self.assertTrue(by_id["dynamic_fields"]["passed"])
        self.assertFalse(by_id["literal_shell_text"]["passed"])

    def test_executed_backticks_are_rejected(self):
        expanded = EXPECTED_B.replace(
            "backtick-literal=`whoami`",
            "backtick-literal=root",
        )

        result = self.grade_snapshots(
            {"output_b": expanded},
            {"output_b": expanded},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["second_document"]["passed"])
        self.assertTrue(by_id["dynamic_fields"]["passed"])
        self.assertFalse(by_id["literal_shell_text"]["passed"])

    def test_hard_coding_first_arguments_fails_second(self):
        result = self.grade_snapshots(
            {"output_b": EXPECTED_A},
            {"output_b": EXPECTED_A},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["first_document"]["passed"])
        self.assertFalse(by_id["second_document"]["passed"])
        self.assertFalse(by_id["dynamic_fields"]["passed"])
        self.assertTrue(by_id["literal_shell_text"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_wrong_line_order_is_rejected(self):
        reordered = (
            "BEGIN NOTICE\n"
            f"owner={OWNER_A}\n"
            f"project={PROJECT_A}\n"
            "home-literal=$HOME\n"
            "command-literal=$(date)\n"
            "backtick-literal=`whoami`\n"
            "END NOTICE\n"
        )

        result = self.grade_snapshots(
            {"output_a": reordered},
            {"output_a": reordered},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["first_document"]["passed"])
        self.assertTrue(by_id["dynamic_fields"]["passed"])
        self.assertTrue(by_id["literal_shell_text"]["passed"])

    def test_append_on_second_run_loses_only_idempotency(self):
        result = self.grade_snapshots(
            {},
            {
                "output_a": EXPECTED_A + EXPECTED_A,
                "output_b": EXPECTED_B + EXPECTED_B,
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["first_document"]["passed"])
        self.assertTrue(by_id["second_document"]["passed"])
        self.assertTrue(by_id["dynamic_fields"]["passed"])
        self.assertTrue(by_id["literal_shell_text"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 85)


if __name__ == "__main__":
    unittest.main()
