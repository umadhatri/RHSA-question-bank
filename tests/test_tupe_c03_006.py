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
    / "TUPE-C03-006"
)

TOKEN = "abc123def456"
BUILD_A = 317
BUILD_B = 842

VARIABLES = {
    "TEST_TOKEN": TOKEN,
    "BUILD_A": BUILD_A,
    "BUILD_B": BUILD_B,
}

OUTPUT_A = f"/workspace/dynamic_a_{TOKEN}.txt"
OUTPUT_B = f"/workspace/dynamic_b_{TOKEN}.txt"
PRODUCER_A = f"/workspace/producer_a_{TOKEN}"
PRODUCER_B = f"/workspace/producer_b_{TOKEN}"
FORMATTER = f"/workspace/formatter_{TOKEN}"


def dynamic_value(prefix: str, build: int) -> str:
    return f"{prefix}-{TOKEN} build-{build} [ready] $literal *"


def producer_text(prefix: str, build: int) -> str:
    value = dynamic_value(prefix, build)
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' '{value}'\n"
    )


def formatter_text() -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        "[[ $# -eq 1 ]] || {\n"
        "    printf 'expected exactly one argument, got %d\\n' \"$#\" >&2\n"
        "    exit 23\n"
        "}\n"
        "\n"
        "printf 'CAPTURED=%s\\n' \"$1\"\n"
    )


EXPECTED_A = f"CAPTURED={dynamic_value('alpha', BUILD_A)}\n"
EXPECTED_B = f"CAPTURED={dynamic_value('beta', BUILD_B)}\n"


def make_snapshot(
    path: Path,
    *,
    output_a: str | None = EXPECTED_A,
    output_b: str | None = EXPECTED_B,
    producer_a: str | None = None,
    producer_b: str | None = None,
    formatter: str | None = None,
    helper_mode: int = 0o755,
) -> None:
    producer_a = (
        producer_text("alpha", BUILD_A)
        if producer_a is None
        else producer_a
    )
    producer_b = (
        producer_text("beta", BUILD_B)
        if producer_b is None
        else producer_b
    )
    formatter = formatter_text() if formatter is None else formatter

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")

        if output_a is not None:
            add_file(tar, OUTPUT_A, output_a)

        if output_b is not None:
            add_file(tar, OUTPUT_B, output_b)

        add_file(tar, PRODUCER_A, producer_a, mode=helper_mode)
        add_file(tar, PRODUCER_B, producer_b, mode=helper_mode)
        add_file(tar, FORMATTER, formatter, mode=helper_mode)


class DynamicCommandReportTests(unittest.TestCase):
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

    def test_missing_second_output_is_rejected(self):
        result = self.grade_snapshots(
            {"output_b": None},
            {"output_b": None},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["first_dynamic_value"]["passed"])
        self.assertFalse(by_id["second_dynamic_value"]["passed"])
        self.assertFalse(by_id["literal_preservation"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_word_splitting_style_output_is_rejected(self):
        split_value = "CAPTURED=alpha-abc123def456\n"

        result = self.grade_snapshots(
            {"output_a": split_value},
            {"output_a": split_value},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["first_dynamic_value"]["passed"])
        self.assertFalse(by_id["literal_preservation"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_hard_coding_first_dynamic_value_fails_second(self):
        result = self.grade_snapshots(
            {"output_b": EXPECTED_A},
            {"output_b": EXPECTED_A},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["first_dynamic_value"]["passed"])
        self.assertFalse(by_id["second_dynamic_value"]["passed"])
        self.assertFalse(by_id["literal_preservation"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_modified_helper_is_rejected(self):
        modified = producer_text("alpha", BUILD_A) + "# modified\n"

        result = self.grade_snapshots(
            {"producer_a": modified},
            {"producer_a": modified},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["first_dynamic_value"]["passed"])
        self.assertTrue(by_id["second_dynamic_value"]["passed"])
        self.assertFalse(by_id["helpers_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_helper_permission_change_is_rejected(self):
        result = self.grade_snapshots(
            {"helper_mode": 0o777},
            {"helper_mode": 0o777},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["helpers_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

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
        self.assertTrue(by_id["first_dynamic_value"]["passed"])
        self.assertTrue(by_id["second_dynamic_value"]["passed"])
        self.assertTrue(by_id["literal_preservation"]["passed"])
        self.assertTrue(by_id["helpers_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 85)


if __name__ == "__main__":
    unittest.main()
