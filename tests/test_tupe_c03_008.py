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
    / "TUPE-C03-008"
)

TOKEN = "abc123def456"
CODE_A = 317
CODE_B = 842

VARIABLES = {
    "TEST_TOKEN": TOKEN,
    "CODE_A": CODE_A,
    "CODE_B": CODE_B,
}

STDOUT_A = f"/workspace/stdout_a_{TOKEN}.txt"
STDERR_A = f"/workspace/stderr_a_{TOKEN}.txt"
STDOUT_B = f"/workspace/stdout_b_{TOKEN}.txt"
STDERR_B = f"/workspace/stderr_b_{TOKEN}.txt"
EMITTER_A = f"/workspace/emitter_a_{TOKEN}"
EMITTER_B = f"/workspace/emitter_b_{TOKEN}"


def stdout_text(prefix: str, code: int) -> str:
    return f"OUT {prefix}-{TOKEN} code-{code} [ok] $literal *\n"


def stderr_text(prefix: str, code: int) -> str:
    return f"ERR {prefix}-{TOKEN} code-{code} [warn] $literal *\n"


def emitter_text(prefix: str, code: int) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' 'OUT {prefix}-{TOKEN} code-{code} [ok] $literal *'\n"
        f"printf '%s\\n' 'ERR {prefix}-{TOKEN} code-{code} [warn] $literal *' >&2\n"
    )


EXPECTED_STDOUT_A = stdout_text("alpha", CODE_A)
EXPECTED_STDERR_A = stderr_text("alpha", CODE_A)
EXPECTED_STDOUT_B = stdout_text("beta", CODE_B)
EXPECTED_STDERR_B = stderr_text("beta", CODE_B)


def make_snapshot(
    path: Path,
    *,
    stdout_a: str | None = EXPECTED_STDOUT_A,
    stderr_a: str | None = EXPECTED_STDERR_A,
    stdout_b: str | None = EXPECTED_STDOUT_B,
    stderr_b: str | None = EXPECTED_STDERR_B,
    emitter_a: str | None = None,
    emitter_b: str | None = None,
    helper_mode: int = 0o755,
) -> None:
    emitter_a = emitter_text("alpha", CODE_A) if emitter_a is None else emitter_a
    emitter_b = emitter_text("beta", CODE_B) if emitter_b is None else emitter_b

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")

        if stdout_a is not None:
            add_file(tar, STDOUT_A, stdout_a)
        if stderr_a is not None:
            add_file(tar, STDERR_A, stderr_a)
        if stdout_b is not None:
            add_file(tar, STDOUT_B, stdout_b)
        if stderr_b is not None:
            add_file(tar, STDERR_B, stderr_b)

        add_file(tar, EMITTER_A, emitter_a, mode=helper_mode)
        add_file(tar, EMITTER_B, emitter_b, mode=helper_mode)


class OutputStreamRouterTests(unittest.TestCase):
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

    def test_merged_streams_are_rejected(self):
        merged_a = EXPECTED_STDOUT_A + EXPECTED_STDERR_A
        merged_b = EXPECTED_STDOUT_B + EXPECTED_STDERR_B

        result = self.grade_snapshots(
            {
                "stdout_a": merged_a,
                "stderr_a": "",
                "stdout_b": merged_b,
                "stderr_b": "",
            },
            {
                "stdout_a": merged_a,
                "stderr_a": "",
                "stdout_b": merged_b,
                "stderr_b": "",
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}
        self.assertFalse(by_id["stdout_routing"]["passed"])
        self.assertFalse(by_id["stderr_routing"]["passed"])
        self.assertFalse(by_id["streams_separated"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_swapped_streams_are_rejected(self):
        result = self.grade_snapshots(
            {
                "stdout_a": EXPECTED_STDERR_A,
                "stderr_a": EXPECTED_STDOUT_A,
                "stdout_b": EXPECTED_STDERR_B,
                "stderr_b": EXPECTED_STDOUT_B,
            },
            {
                "stdout_a": EXPECTED_STDERR_A,
                "stderr_a": EXPECTED_STDOUT_A,
                "stdout_b": EXPECTED_STDERR_B,
                "stderr_b": EXPECTED_STDOUT_B,
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}
        self.assertFalse(by_id["stdout_routing"]["passed"])
        self.assertFalse(by_id["stderr_routing"]["passed"])
        self.assertFalse(by_id["streams_separated"]["passed"])

    def test_missing_stderr_file_is_rejected(self):
        result = self.grade_snapshots(
            {"stderr_b": None},
            {"stderr_b": None},
        )

        by_id = {item["id"]: item for item in result["tests"]}
        self.assertFalse(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["stdout_routing"]["passed"])
        self.assertFalse(by_id["stderr_routing"]["passed"])
        self.assertFalse(by_id["streams_separated"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_hard_coding_first_emitter_fails_second(self):
        result = self.grade_snapshots(
            {
                "stdout_b": EXPECTED_STDOUT_A,
                "stderr_b": EXPECTED_STDERR_A,
            },
            {
                "stdout_b": EXPECTED_STDOUT_A,
                "stderr_b": EXPECTED_STDERR_A,
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}
        self.assertFalse(by_id["stdout_routing"]["passed"])
        self.assertFalse(by_id["stderr_routing"]["passed"])
        self.assertFalse(by_id["streams_separated"]["passed"])

    def test_modified_helper_is_rejected(self):
        modified = emitter_text("alpha", CODE_A) + "# modified\n"

        result = self.grade_snapshots(
            {"emitter_a": modified},
            {"emitter_a": modified},
        )

        by_id = {item["id"]: item for item in result["tests"]}
        self.assertTrue(by_id["stdout_routing"]["passed"])
        self.assertTrue(by_id["stderr_routing"]["passed"])
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
                "stdout_a": EXPECTED_STDOUT_A + EXPECTED_STDOUT_A,
                "stderr_a": EXPECTED_STDERR_A + EXPECTED_STDERR_A,
                "stdout_b": EXPECTED_STDOUT_B + EXPECTED_STDOUT_B,
                "stderr_b": EXPECTED_STDERR_B + EXPECTED_STDERR_B,
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}
        self.assertTrue(by_id["outputs_created"]["passed"])
        self.assertTrue(by_id["stdout_routing"]["passed"])
        self.assertTrue(by_id["stderr_routing"]["passed"])
        self.assertTrue(by_id["streams_separated"]["passed"])
        self.assertTrue(by_id["helpers_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 85)


if __name__ == "__main__":
    unittest.main()
