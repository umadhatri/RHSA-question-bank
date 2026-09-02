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
    / "TUPE-C03-002"
)

TOKEN = "abc123def456"
LOG_START = 3
REPORT_START = 5
OUTPUT = f"/workspace/pattern_report_{TOKEN}.txt"

VARIABLES = {
    "TEST_TOKEN": TOKEN,
    "LOG_START": LOG_START,
    "REPORT_START": REPORT_START,
}


def expected_sections() -> dict[str, list[str]]:
    return {
        "[SINGLE_CHAR_LOGS]": [
            "app3.log",
            "app4.log",
            "app5.log",
        ],
        "[NUMBERED_REPORTS]": [
            "report5.txt",
            "report6.txt",
            "report7.txt",
        ],
        "[BACKUPS]": [
            f"archive_{TOKEN}.old",
            f"config_{TOKEN}.old",
            f"notes_{TOKEN}.old",
        ],
    }


def render_report(
    *,
    single: list[str] | None = None,
    reports: list[str] | None = None,
    backups: list[str] | None = None,
) -> str:
    expected = expected_sections()

    single = expected["[SINGLE_CHAR_LOGS]"] if single is None else single
    reports = expected["[NUMBERED_REPORTS]"] if reports is None else reports
    backups = expected["[BACKUPS]"] if backups is None else backups

    lines = [
        "[SINGLE_CHAR_LOGS]",
        *single,
        "",
        "[NUMBERED_REPORTS]",
        *reports,
        "",
        "[BACKUPS]",
        *backups,
    ]

    return "\n".join(lines) + "\n"


def make_snapshot(path: Path, text: str | None) -> None:
    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        if text is not None:
            add_file(tar, OUTPUT, text)


class FilenamePatternSelectorTests(unittest.TestCase):
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
        first_text: str | None,
        second_text: str | None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"

            make_snapshot(first, first_text)
            make_snapshot(second, second_text)

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
        text = render_report()
        result = self.grade_snapshots(text, text)

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_broad_app_glob_is_rejected(self):
        broad = [
            "app3.log",
            "app4.log",
            "app5.log",
            "app34.log",
        ]

        text = render_report(single=broad)
        result = self.grade_snapshots(text, text)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["single_char_logs"]["passed"])
        self.assertFalse(by_id["exact_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_broad_report_glob_is_rejected(self):
        broad = [
            "report5.txt",
            "report6.txt",
            "report7.txt",
            "report56.txt",
            "reportA.txt",
        ]

        text = render_report(reports=broad)
        result = self.grade_snapshots(text, text)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["numbered_reports"]["passed"])
        self.assertFalse(by_id["exact_report"]["passed"])

    def test_hidden_backup_is_rejected(self):
        backups = [
            f".secret_{TOKEN}.old",
            f"archive_{TOKEN}.old",
            f"config_{TOKEN}.old",
            f"notes_{TOKEN}.old",
        ]

        text = render_report(backups=backups)
        result = self.grade_snapshots(text, text)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["backup_files"]["passed"])
        self.assertFalse(by_id["exact_report"]["passed"])

    def test_append_on_second_run_loses_idempotency(self):
        first = render_report()
        second = first + first

        result = self.grade_snapshots(first, second)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["single_char_logs"]["passed"])
        self.assertTrue(by_id["numbered_reports"]["passed"])
        self.assertTrue(by_id["backup_files"]["passed"])
        self.assertTrue(by_id["exact_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
