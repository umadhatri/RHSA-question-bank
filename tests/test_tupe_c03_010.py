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
    / "TUPE-C03-010"
)

TOKEN = "abc123def456"
VARIABLES = {
    "TEST_TOKEN": TOKEN,
}

BASE = f"/workspace/batch_{TOKEN}"
OUTPUT_SHORT = f"/workspace/batch_short_{TOKEN}.txt"
OUTPUT_LONG = f"/workspace/batch_long_{TOKEN}.txt"

SOURCES = [
    (
        f"{BASE}/alpha one.txt",
        f"alpha-{TOKEN} first\nalpha second\n",
        2,
    ),
    (
        f"{BASE}/beta[2].txt",
        f"beta-{TOKEN} first\nbeta second\nbeta third\n",
        3,
    ),
    (
        f"{BASE}/gamma*.txt",
        f"gamma-{TOKEN} only\n",
        1,
    ),
    (
        f"{BASE}/delta dollar$.txt",
        f"delta-{TOKEN} one\ndelta two\ndelta three\ndelta four\n",
        4,
    ),
    (
        f"{BASE}/epsilon-empty.txt",
        "",
        0,
    ),
    (
        f"{BASE}/decoy-not-supplied.txt",
        f"DECOY-{TOKEN} one\nDECOY two\nDECOY three\nDECOY four\nDECOY five\n",
        5,
    ),
]


def record(path: str, count: int) -> str:
    name = path.rsplit("/", 1)[-1]
    return f"FILE={name}\nLINES={count}\n"


EXPECTED_SHORT = "".join(
    record(path, count)
    for path, _text, count in SOURCES[:2]
)

EXPECTED_LONG = "".join(
    record(path, count)
    for path, _text, count in SOURCES[:5]
)

DECOY_RECORD = record(SOURCES[5][0], SOURCES[5][2])


def make_snapshot(
    path: Path,
    *,
    short_text: str | None = EXPECTED_SHORT,
    long_text: str | None = EXPECTED_LONG,
    source_overrides: dict[str, str] | None = None,
    source_mode: int = 0o644,
) -> None:
    source_overrides = source_overrides or {}

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        add_dir(tar, BASE)

        if short_text is not None:
            add_file(tar, OUTPUT_SHORT, short_text)

        if long_text is not None:
            add_file(tar, OUTPUT_LONG, long_text)

        for source_path, source_text, _count in SOURCES:
            add_file(
                tar,
                source_path,
                source_overrides.get(source_path, source_text),
                mode=source_mode,
            )


class BatchFileProcessorTests(unittest.TestCase):
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

    def test_missing_long_report_is_rejected(self):
        result = self.grade_snapshots(
            {"long_text": None},
            {"long_text": None},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["short_batch"]["passed"])
        self.assertFalse(by_id["long_batch"]["passed"])
        self.assertFalse(by_id["counts"]["passed"])
        self.assertFalse(by_id["order_and_quoting"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_fixed_two_file_solution_fails_long_invocation(self):
        truncated = "".join(
            record(path, count)
            for path, _text, count in SOURCES[:2]
        )

        result = self.grade_snapshots(
            {"long_text": truncated},
            {"long_text": truncated},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["short_batch"]["passed"])
        self.assertFalse(by_id["long_batch"]["passed"])
        self.assertFalse(by_id["counts"]["passed"])
        self.assertFalse(by_id["order_and_quoting"]["passed"])

    def test_reordered_files_are_rejected(self):
        reordered = "".join(
            record(path, count)
            for path, _text, count in [
                SOURCES[1],
                SOURCES[0],
                *SOURCES[2:5],
            ]
        )

        result = self.grade_snapshots(
            {"long_text": reordered},
            {"long_text": reordered},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_batch"]["passed"])
        self.assertTrue(by_id["counts"]["passed"])
        self.assertFalse(by_id["order_and_quoting"]["passed"])

    def test_directory_glob_that_includes_decoy_is_rejected(self):
        result = self.grade_snapshots(
            {"long_text": EXPECTED_LONG + DECOY_RECORD},
            {"long_text": EXPECTED_LONG + DECOY_RECORD},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_batch"]["passed"])
        self.assertFalse(by_id["counts"]["passed"])
        self.assertFalse(by_id["order_and_quoting"]["passed"])

    def test_space_and_metacharacter_filename_damage_is_rejected(self):
        damaged = EXPECTED_LONG.replace(
            "FILE=alpha one.txt",
            "FILE=alpha",
        ).replace(
            "FILE=gamma*.txt",
            "FILE=gammaX.txt",
        )

        result = self.grade_snapshots(
            {"long_text": damaged},
            {"long_text": damaged},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_batch"]["passed"])
        self.assertTrue(by_id["counts"]["passed"])
        self.assertFalse(by_id["order_and_quoting"]["passed"])

    def test_modified_source_file_is_rejected(self):
        modified_path = SOURCES[0][0]
        modified_text = SOURCES[0][1] + "modified\n"

        result = self.grade_snapshots(
            {
                "source_overrides": {
                    modified_path: modified_text,
                }
            },
            {
                "source_overrides": {
                    modified_path: modified_text,
                }
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["short_batch"]["passed"])
        self.assertTrue(by_id["long_batch"]["passed"])
        self.assertFalse(by_id["sources_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_source_permission_change_is_rejected(self):
        result = self.grade_snapshots(
            {"source_mode": 0o666},
            {"source_mode": 0o666},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["sources_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_append_on_second_run_loses_only_idempotency(self):
        result = self.grade_snapshots(
            {},
            {
                "short_text": EXPECTED_SHORT + EXPECTED_SHORT,
                "long_text": EXPECTED_LONG + EXPECTED_LONG,
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["short_batch"]["passed"])
        self.assertTrue(by_id["long_batch"]["passed"])
        self.assertTrue(by_id["counts"]["passed"])
        self.assertTrue(by_id["order_and_quoting"]["passed"])
        self.assertTrue(by_id["sources_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
