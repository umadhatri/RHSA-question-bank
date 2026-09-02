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
    / "TUPE-C03-003"
)

TOKEN = "abc123def456"
OUTPUT = f"/workspace/quote report {TOKEN} ?.txt"


def expected_label() -> str:
    return f"Batch  {TOKEN}  *  ?  semi;colon"


def expected_values() -> dict[str, str]:
    return {
        "customer": f"Customer record {TOKEN} with spaces",
        "price": f"Price tier {TOKEN} dollar-four",
        "pattern": f"Pattern literal {TOKEN} star",
        "question": f"Question literal {TOKEN} mark",
    }


def render_report(
    *,
    label: str | None = None,
    values: dict[str, str] | None = None,
) -> str:
    label = expected_label() if label is None else label
    values = expected_values() if values is None else values

    return (
        "[LABEL]\n"
        f"{label}\n"
        "\n"
        "[FILES]\n"
        f"customer={values.get('customer', '')}\n"
        f"price={values.get('price', '')}\n"
        f"pattern={values.get('pattern', '')}\n"
        f"question={values.get('question', '')}\n"
    )


def make_snapshot(path: Path, text: str | None) -> None:
    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        if text is not None:
            add_file(tar, OUTPUT, text)


class QuotingAndLiteralDataTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text(encoding="utf-8")
        )

        self.context = {
            "syntax_ok": True,
            "variables": {
                "TEST_TOKEN": TOKEN,
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

    def test_collapsed_label_spacing_is_rejected(self):
        bad_label = f"Batch {TOKEN} * ? semi;colon"
        text = render_report(label=bad_label)

        result = self.grade_snapshots(text, text)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["label_preserved"]["passed"])
        self.assertFalse(by_id["exact_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_decoy_value_is_rejected(self):
        values = expected_values()
        values["pattern"] = f"DECOY pattern A {TOKEN}"

        text = render_report(values=values)
        result = self.grade_snapshots(text, text)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["label_preserved"]["passed"])
        self.assertFalse(by_id["special_file_values"]["passed"])
        self.assertFalse(by_id["exact_report"]["passed"])

    def test_missing_output_loses_output_and_content_points(self):
        result = self.grade_snapshots(None, None)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["output_created"]["passed"])
        self.assertFalse(by_id["label_preserved"]["passed"])
        self.assertFalse(by_id["special_file_values"]["passed"])
        self.assertFalse(by_id["exact_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_append_on_second_run_loses_only_idempotency(self):
        first = render_report()
        second = first + first

        result = self.grade_snapshots(first, second)
        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["label_preserved"]["passed"])
        self.assertTrue(by_id["special_file_values"]["passed"])
        self.assertTrue(by_id["exact_report"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
