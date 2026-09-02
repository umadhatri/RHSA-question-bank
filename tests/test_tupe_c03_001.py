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
    / "TUPE-C03-001"
)
TOKEN = "abc123def456"
OUTPUT = f"/workspace/error_report_{TOKEN}.txt"


def expected_lines() -> list[str]:
    return sorted(
        {
            f"ERROR alpha-{TOKEN} disk-threshold",
            f"ERROR beta-{TOKEN} queue-backlog",
            f"ERROR shared-{TOKEN} authentication-retry",
            f"ERROR zeta-{TOKEN} service-unavailable",
        }
    )


def make_snapshot(path: Path, lines: list[str] | None) -> None:
    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        if lines is not None:
            content = "\n".join(lines)
            if lines:
                content += "\n"
            add_file(tar, OUTPUT, content)


class PipelineReportBuilderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text(encoding="utf-8")
        )
        self.context = {
            "syntax_ok": True,
            "variables": {"TEST_TOKEN": TOKEN},
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
        first_lines: list[str] | None,
        second_lines: list[str] | None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"

            make_snapshot(first, first_lines)
            make_snapshot(second, second_lines)

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

    def test_complete_report_scores_100(self):
        expected = expected_lines()
        result = self.grade_snapshots(expected, expected)

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_missing_second_source_loses_source_and_exactness_points(self):
        incomplete = [
            f"ERROR alpha-{TOKEN} disk-threshold",
            f"ERROR shared-{TOKEN} authentication-retry",
        ]

        result = self.grade_snapshots(incomplete, incomplete)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["error_filtering"]["passed"])
        self.assertFalse(by_id["both_sources"]["passed"])
        self.assertFalse(by_id["sorted_unique_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_duplicate_or_unsorted_output_fails_exact_report_check(self):
        expected = expected_lines()
        malformed = [
            expected[2],
            expected[0],
            expected[1],
            expected[2],
            expected[3],
        ]

        result = self.grade_snapshots(malformed, malformed)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["error_filtering"]["passed"])
        self.assertTrue(by_id["both_sources"]["passed"])
        self.assertFalse(by_id["sorted_unique_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_stale_non_error_content_fails_filtering(self):
        stale = [
            f"STALE REPORT {TOKEN}",
            *expected_lines(),
        ]

        result = self.grade_snapshots(stale, stale)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["error_filtering"]["passed"])
        self.assertFalse(by_id["sorted_unique_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_second_run_append_regression_loses_only_idempotency(self):
        first = expected_lines()
        second = [
            *expected_lines(),
            *expected_lines(),
        ]

        result = self.grade_snapshots(first, second)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["sorted_unique_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
