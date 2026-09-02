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
    / "TUPE-C03-005"
)

TOKEN = "abc123def456"
SHORT = f"/workspace/short_manifest_{TOKEN}.txt"
LONG = f"/workspace/long_manifest_{TOKEN}.txt"

ITEMS = [
    f"alpha-{TOKEN}",
    f"beta-{TOKEN}",
    f"gamma-{TOKEN}",
    f"delta-{TOKEN}",
]

VARIABLES = {
    "TEST_TOKEN": TOKEN,
}


def manifest(label: str, items: list[str]) -> str:
    lines = [
        f"LABEL={label}",
        f"COUNT={len(items)}",
    ]

    lines.extend(
        f"{index}={item}"
        for index, item in enumerate(items, start=1)
    )

    return "\n".join(lines) + "\n"


EXPECTED_SHORT = manifest(
    f"short-{TOKEN}",
    ITEMS[:2],
)

EXPECTED_LONG = manifest(
    f"long-{TOKEN}",
    ITEMS,
)


def make_snapshot(
    path: Path,
    *,
    short_text: str | None = EXPECTED_SHORT,
    long_text: str | None = EXPECTED_LONG,
) -> None:
    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")

        if short_text is not None:
            add_file(tar, SHORT, short_text)

        if long_text is not None:
            add_file(tar, LONG, long_text)


class ArgumentManifestBuilderTests(unittest.TestCase):
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

    def test_missing_long_output_is_rejected(self):
        result = self.grade_snapshots(
            {"long_text": None},
            {"long_text": None},
        )

        by_id = {
            item["id"]: item
            for item in result["tests"]
        }

        self.assertFalse(by_id["outputs_created"]["passed"])
        self.assertFalse(by_id["long_manifest"]["passed"])
        self.assertFalse(by_id["labels_and_counts"]["passed"])
        self.assertFalse(by_id["argument_order"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_fixed_count_two_solution_fails_long_invocation(self):
        bad_long = manifest(
            f"long-{TOKEN}",
            ITEMS[:2],
        )

        result = self.grade_snapshots(
            {"long_text": bad_long},
            {"long_text": bad_long},
        )

        by_id = {
            item["id"]: item
            for item in result["tests"]
        }

        self.assertTrue(by_id["short_manifest"]["passed"])
        self.assertFalse(by_id["long_manifest"]["passed"])
        self.assertFalse(by_id["labels_and_counts"]["passed"])
        self.assertFalse(by_id["argument_order"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_wrong_count_is_rejected_even_when_items_exist(self):
        bad_long = EXPECTED_LONG.replace(
            "COUNT=4\n",
            "COUNT=2\n",
            1,
        )

        result = self.grade_snapshots(
            {"long_text": bad_long},
            {"long_text": bad_long},
        )

        by_id = {
            item["id"]: item
            for item in result["tests"]
        }

        self.assertFalse(by_id["long_manifest"]["passed"])
        self.assertFalse(by_id["labels_and_counts"]["passed"])
        self.assertTrue(by_id["argument_order"]["passed"])

    def test_reordered_items_are_rejected(self):
        reordered = [
            ITEMS[1],
            ITEMS[0],
            ITEMS[2],
            ITEMS[3],
        ]

        bad_long = manifest(
            f"long-{TOKEN}",
            reordered,
        )

        result = self.grade_snapshots(
            {"long_text": bad_long},
            {"long_text": bad_long},
        )

        by_id = {
            item["id"]: item
            for item in result["tests"]
        }

        self.assertFalse(by_id["long_manifest"]["passed"])
        self.assertTrue(by_id["labels_and_counts"]["passed"])
        self.assertFalse(by_id["argument_order"]["passed"])

    def test_append_on_second_run_loses_only_idempotency(self):
        result = self.grade_snapshots(
            {},
            {
                "short_text": EXPECTED_SHORT + EXPECTED_SHORT,
                "long_text": EXPECTED_LONG + EXPECTED_LONG,
            },
        )

        by_id = {
            item["id"]: item
            for item in result["tests"]
        }

        self.assertTrue(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["short_manifest"]["passed"])
        self.assertTrue(by_id["long_manifest"]["passed"])
        self.assertTrue(by_id["labels_and_counts"]["passed"])
        self.assertTrue(by_id["argument_order"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
