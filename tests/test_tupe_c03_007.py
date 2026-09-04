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
    / "TUPE-C03-007"
)

TOKEN = "abc123def456"

VARIABLES = {
    "TEST_TOKEN": TOKEN,
}

OUTPUT_A = f"/workspace/environment_a_{TOKEN}.txt"
OUTPUT_B = f"/workspace/environment_b_{TOKEN}.txt"

TOOL_A_DIR = f"/workspace/tool_a_{TOKEN}"
TOOL_B_DIR = f"/workspace/tool_b_{TOKEN}"
DECOY_DIR = f"/workspace/decoy_bin_{TOKEN}"
LEGACY_DIR = f"/workspace/legacy_bin_{TOKEN}"

TOOL_A = f"{TOOL_A_DIR}/range-tool"
TOOL_B = f"{TOOL_B_DIR}/range-tool"
DECOY = f"{DECOY_DIR}/range-tool"
LEGACY = f"{LEGACY_DIR}/legacy-helper"
PROBE = f"/workspace/environment_probe_{TOKEN}"

SESSION_A = f"alpha session {TOKEN}"
SESSION_B = f"beta session {TOKEN}"

BASE_PATH = f"{DECOY_DIR}:{LEGACY_DIR}:/usr/local/bin:/usr/bin:/bin"
PATH_A = f"{TOOL_A_DIR}:{BASE_PATH}"
PATH_B = f"{TOOL_B_DIR}:{BASE_PATH}"


def tool_text(value: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' '{value}-{TOKEN}'\n"
    )


def probe_text() -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "\n"
        "resolved_tool=$(command -v range-tool 2>/dev/null || true)\n"
        "tool_value=$(range-tool 2>/dev/null || true)\n"
        "resolved_legacy=$(command -v legacy-helper 2>/dev/null || true)\n"
        "legacy_value=$(legacy-helper 2>/dev/null || true)\n"
        "\n"
        "printf 'SESSION=%s\\n' \"${TUPE_SESSION-<unset>}\"\n"
        "printf 'RESOLVED_TOOL=%s\\n' \"$resolved_tool\"\n"
        "printf 'TOOL_VALUE=%s\\n' \"$tool_value\"\n"
        "printf 'RESOLVED_LEGACY=%s\\n' \"$resolved_legacy\"\n"
        "printf 'LEGACY_VALUE=%s\\n' \"$legacy_value\"\n"
        "printf 'PATH=%s\\n' \"$PATH\"\n"
    )


def expected_report(
    session: str,
    tool_path: str,
    tool_value: str,
    path_value: str,
) -> str:
    return (
        f"SESSION={session}\n"
        f"RESOLVED_TOOL={tool_path}\n"
        f"TOOL_VALUE={tool_value}\n"
        f"RESOLVED_LEGACY={LEGACY}\n"
        f"LEGACY_VALUE=legacy-{TOKEN}\n"
        f"PATH={path_value}\n"
    )


EXPECTED_A = expected_report(
    SESSION_A,
    TOOL_A,
    f"alpha-{TOKEN}",
    PATH_A,
)
EXPECTED_B = expected_report(
    SESSION_B,
    TOOL_B,
    f"beta-{TOKEN}",
    PATH_B,
)


def make_snapshot(
    path: Path,
    *,
    output_a: str | None = EXPECTED_A,
    output_b: str | None = EXPECTED_B,
    tool_a_text: str | None = None,
    helper_mode: int = 0o755,
) -> None:
    tool_a_text = tool_text("alpha") if tool_a_text is None else tool_a_text

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/workspace")
        add_dir(tar, TOOL_A_DIR)
        add_dir(tar, TOOL_B_DIR)
        add_dir(tar, DECOY_DIR)
        add_dir(tar, LEGACY_DIR)

        if output_a is not None:
            add_file(tar, OUTPUT_A, output_a)

        if output_b is not None:
            add_file(tar, OUTPUT_B, output_b)

        add_file(tar, TOOL_A, tool_a_text, mode=helper_mode)
        add_file(tar, TOOL_B, tool_text("beta"), mode=helper_mode)
        add_file(tar, DECOY, tool_text("decoy"), mode=helper_mode)
        add_file(tar, LEGACY, tool_text("legacy"), mode=helper_mode)
        add_file(tar, PROBE, probe_text(), mode=helper_mode)


class EnvironmentAndPathRepairTests(unittest.TestCase):
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

    def test_unexported_session_is_rejected(self):
        bad_a = EXPECTED_A.replace(
            f"SESSION={SESSION_A}\n",
            "SESSION=<unset>\n",
        )
        bad_b = EXPECTED_B.replace(
            f"SESSION={SESSION_B}\n",
            "SESSION=<unset>\n",
        )

        result = self.grade_snapshots(
            {"output_a": bad_a, "output_b": bad_b},
            {"output_a": bad_a, "output_b": bad_b},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertFalse(by_id["session_export"]["passed"])
        self.assertTrue(by_id["path_precedence"]["passed"])
        self.assertTrue(by_id["path_preservation"]["passed"])
        self.assertFalse(by_id["exact_reports"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_appending_tool_directory_uses_decoy(self):
        append_path_a = f"{BASE_PATH}:{TOOL_A_DIR}"
        append_path_b = f"{BASE_PATH}:{TOOL_B_DIR}"

        bad_a = expected_report(
            SESSION_A,
            DECOY,
            f"decoy-{TOKEN}",
            append_path_a,
        )
        bad_b = expected_report(
            SESSION_B,
            DECOY,
            f"decoy-{TOKEN}",
            append_path_b,
        )

        result = self.grade_snapshots(
            {"output_a": bad_a, "output_b": bad_b},
            {"output_a": bad_a, "output_b": bad_b},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["session_export"]["passed"])
        self.assertFalse(by_id["path_precedence"]["passed"])
        self.assertFalse(by_id["path_preservation"]["passed"])
        self.assertFalse(by_id["exact_reports"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_replacing_path_loses_legacy_helper(self):
        bad_a = (
            f"SESSION={SESSION_A}\n"
            f"RESOLVED_TOOL={TOOL_A}\n"
            f"TOOL_VALUE=alpha-{TOKEN}\n"
            "RESOLVED_LEGACY=\n"
            "LEGACY_VALUE=\n"
            f"PATH={TOOL_A_DIR}\n"
        )
        bad_b = (
            f"SESSION={SESSION_B}\n"
            f"RESOLVED_TOOL={TOOL_B}\n"
            f"TOOL_VALUE=beta-{TOKEN}\n"
            "RESOLVED_LEGACY=\n"
            "LEGACY_VALUE=\n"
            f"PATH={TOOL_B_DIR}\n"
        )

        result = self.grade_snapshots(
            {"output_a": bad_a, "output_b": bad_b},
            {"output_a": bad_a, "output_b": bad_b},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["session_export"]["passed"])
        self.assertTrue(by_id["path_precedence"]["passed"])
        self.assertFalse(by_id["path_preservation"]["passed"])
        self.assertFalse(by_id["exact_reports"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_hard_coding_first_tool_directory_fails_second(self):
        bad_b = expected_report(
            SESSION_B,
            TOOL_A,
            f"alpha-{TOKEN}",
            PATH_A,
        )

        result = self.grade_snapshots(
            {"output_b": bad_b},
            {"output_b": bad_b},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["session_export"]["passed"])
        self.assertFalse(by_id["path_precedence"]["passed"])
        self.assertFalse(by_id["path_preservation"]["passed"])
        self.assertFalse(by_id["exact_reports"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])

    def test_modified_helper_is_rejected(self):
        modified = tool_text("alpha") + "# modified\n"

        result = self.grade_snapshots(
            {"tool_a_text": modified},
            {"tool_a_text": modified},
        )

        by_id = {item["id"]: item for item in result["tests"]}

        self.assertTrue(by_id["exact_reports"]["passed"])
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
        self.assertTrue(by_id["session_export"]["passed"])
        self.assertTrue(by_id["path_precedence"]["passed"])
        self.assertTrue(by_id["path_preservation"]["passed"])
        self.assertTrue(by_id["exact_reports"]["passed"])
        self.assertTrue(by_id["helpers_preserved"]["passed"])
        self.assertFalse(by_id["idempotency"]["passed"])
        self.assertEqual(result["score"], 90)


if __name__ == "__main__":
    unittest.main()
