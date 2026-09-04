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
    / "TUPE-C03-011"
)

TOKEN = "abc123def456"
VARIABLES = {
    "TEST_TOKEN": TOKEN,
}

SOURCE_DIR = f"/workspace/bundle_sources_{TOKEN}"
SHORT_DIR = f"/workspace/extract_short_{TOKEN}"
LONG_DIR = f"/workspace/extract_long_{TOKEN}"
BUNDLE_SHORT = f"/workspace/bundle_short_{TOKEN}.sh"
BUNDLE_LONG = f"/workspace/bundle_long_{TOKEN}.sh"

SOURCES = [
    (
        f"{SOURCE_DIR}/alpha note.txt",
        (
            f"alpha-{TOKEN}\n"
            "$HOME must remain literal\n"
            "$(date) must remain literal\n"
            "EOF\n"
        ).encode(),
    ),
    (
        f"{SOURCE_DIR}/beta[2].conf",
        (
            f"beta-{TOKEN}\n"
            "backtick: `whoami`\n"
            "single quote: 'alpha'\n"
            'double quote: "beta"\n'
            "backslash: \\\n"
        ).encode(),
    ),
    (
        f"{SOURCE_DIR}/gamma*.txt",
        (
            f"gamma-{TOKEN} first\n"
            "\n"
            "middle blank line above\n"
            "__TUPE_BUNDLE_3__\n"
            "gamma final\n"
        ).encode(),
    ),
    (
        f"{SOURCE_DIR}/delta dollar$.txt",
        (
            f"delta-{TOKEN}\n"
            "END_BUNDLE\n"
            "$literal * [brackets]\n"
        ).encode(),
    ),
    (
        f"{SOURCE_DIR}/epsilon-empty.txt",
        b"",
    ),
    (
        f"{SOURCE_DIR}/decoy-not-supplied.txt",
        (
            f"DECOY-{TOKEN}\n"
            "this file must never be bundled\n"
        ).encode(),
    ),
]

DEFAULT_BUNDLE_SHORT = b"#!/usr/bin/env bash\n# short bundle\n"
DEFAULT_BUNDLE_LONG = b"#!/usr/bin/env bash\n# long bundle\n"


def basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def expected_short() -> dict[str, bytes]:
    return {basename(path): content for path, content in SOURCES[:2]}


def expected_long() -> dict[str, bytes]:
    return {basename(path): content for path, content in SOURCES[:5]}


def make_snapshot(
    path: Path,
    *,
    bundle_short: bytes | None = DEFAULT_BUNDLE_SHORT,
    bundle_long: bytes | None = DEFAULT_BUNDLE_LONG,
    short_files: dict[str, bytes] | None = None,
    long_files: dict[str, bytes] | None = None,
    source_overrides: dict[str, bytes] | None = None,
    source_mode: int = 0o644,
) -> None:
    short_files = expected_short() if short_files is None else short_files
    long_files = expected_long() if long_files is None else long_files
    source_overrides = source_overrides or {}

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        add_dir(tar, SOURCE_DIR)
        add_dir(tar, SHORT_DIR)
        add_dir(tar, LONG_DIR)

        if bundle_short is not None:
            add_file(tar, BUNDLE_SHORT, bundle_short)

        if bundle_long is not None:
            add_file(tar, BUNDLE_LONG, bundle_long)

        for source_path, source_content in SOURCES:
            add_file(
                tar,
                source_path,
                source_overrides.get(source_path, source_content),
                mode=source_mode,
            )

        for name, content in short_files.items():
            add_file(tar, f"{SHORT_DIR}/{name}", content)

        for name, content in long_files.items():
            add_file(tar, f"{LONG_DIR}/{name}", content)


class BundleBuilderTests(unittest.TestCase):
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
        context_overrides: dict | None = None,
    ) -> dict:
        first_kwargs = first_kwargs or {}
        second_kwargs = second_kwargs or {}
        context = dict(self.context)
        if context_overrides:
            context.update(context_overrides)

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
                    context,
                    snapshots,
                )

    def test_complete_state_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_missing_long_bundle_is_rejected(self):
        result = self.grade_snapshots(
            {"bundle_long": None},
            {"bundle_long": None},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["bundles_created"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_missing_long_reconstructed_file_is_rejected(self):
        damaged = expected_long()
        damaged.pop("delta dollar$.txt")

        result = self.grade_snapshots(
            {"long_files": damaged},
            {"long_files": damaged},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_reconstruction"]["passed"])
        self.assertFalse(by_id["no_extra_files"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_fixed_two_file_solution_fails_long_bundle(self):
        result = self.grade_snapshots(
            {"long_files": expected_short()},
            {"long_files": expected_short()},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["short_reconstruction"]["passed"])
        self.assertFalse(by_id["long_reconstruction"]["passed"])
        self.assertFalse(by_id["no_extra_files"]["passed"])

    def test_unsupplied_decoy_is_rejected(self):
        long_files = expected_long()
        decoy_path, decoy_content = SOURCES[5]
        long_files[basename(decoy_path)] = decoy_content

        result = self.grade_snapshots(
            {"long_files": long_files},
            {"long_files": long_files},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_reconstruction"]["passed"])
        self.assertFalse(by_id["no_extra_files"]["passed"])

    def test_shell_expansion_damage_is_rejected(self):
        short_files = expected_short()
        short_files["alpha note.txt"] = SOURCES[0][1].replace(
            b"$HOME must remain literal",
            b"/root must remain literal",
        )

        result = self.grade_snapshots(
            {"short_files": short_files},
            {"short_files": short_files},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["short_reconstruction"]["passed"])
        self.assertFalse(by_id["literal_preservation"]["passed"])

    def test_here_document_delimiter_collision_damage_is_rejected(self):
        long_files = expected_long()
        long_files["gamma*.txt"] = (
            f"gamma-{TOKEN} first\n\n"
            "middle blank line above\n"
        ).encode()

        result = self.grade_snapshots(
            {"long_files": long_files},
            {"long_files": long_files},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_reconstruction"]["passed"])
        self.assertFalse(by_id["literal_preservation"]["passed"])

    def test_empty_file_with_newline_is_rejected(self):
        long_files = expected_long()
        long_files["epsilon-empty.txt"] = b"\n"

        result = self.grade_snapshots(
            {"long_files": long_files},
            {"long_files": long_files},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["long_reconstruction"]["passed"])
        self.assertFalse(by_id["empty_file"]["passed"])

    def test_modified_source_is_rejected(self):
        source_path, source_content = SOURCES[0]

        result = self.grade_snapshots(
            {
                "source_overrides": {
                    source_path: source_content + b"modified\n",
                }
            },
            {
                "source_overrides": {
                    source_path: source_content + b"modified\n",
                }
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}

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

    def test_first_execution_failure_is_rejected(self):
        result = self.grade_snapshots(
            context_overrides={
                "first_run": {
                    "returncode": 1,
                    "timed_out": False,
                }
            }
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["first_run_exit"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_changed_bundle_on_second_run_loses_only_idempotency(self):
        result = self.grade_snapshots(
            {},
            {
                "bundle_short": DEFAULT_BUNDLE_SHORT + b"# changed\n",
                "bundle_long": DEFAULT_BUNDLE_LONG + b"# changed\n",
            },
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["bundles_created"]["passed"])
        self.assertTrue(by_id["short_reconstruction"]["passed"])
        self.assertTrue(by_id["long_reconstruction"]["passed"])
        self.assertTrue(by_id["literal_preservation"]["passed"])
        self.assertTrue(by_id["empty_file"]["passed"])
        self.assertTrue(by_id["no_extra_files"]["passed"])
        self.assertTrue(by_id["sources_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 85)


if __name__ == "__main__":
    unittest.main()
