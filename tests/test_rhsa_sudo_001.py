from __future__ import annotations

import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet


ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "06-privileged-access" / "RHSA-SUDO-001"

USERNAME = "student_123456"
DROPIN = f"/etc/sudoers.d/cyberrange-{USERNAME}"
HELPER = "/usr/local/sbin/cyberrange-maintenance"

SUDOERS_CONTENT = (
    "Defaults secure_path=/usr/local/sbin:/usr/local/bin:"
    "/usr/sbin:/usr/bin:/sbin:/bin\n"
    "@includedir /etc/sudoers.d\n"
)

HELPER_CONTENT = (
    "#!/usr/bin/env bash\n"
    "set -euo pipefail\n"
    "printf 'maintenance-ok\\n'\n"
)

SUDO_BINARY_CONTENT = "fake-sudo-binary-for-unit-test\n"
VISUDO_BINARY_CONTENT = "fake-visudo-binary-for-unit-test\n"

GOOD_RULE = (
    f"{USERNAME} ALL=(root) NOPASSWD: "
    f"{HELPER}\n"
)

GOOD_SUDO_LIST = (
    f"User {USERNAME} may run the following commands:\n"
    f"    (root) NOPASSWD: {HELPER}\n"
)

BROAD_RULE = (
    f"{USERNAME} ALL=(ALL) NOPASSWD: ALL\n"
)

BROAD_SUDO_LIST = (
    f"User {USERNAME} may run the following commands:\n"
    "    (ALL) NOPASSWD: ALL\n"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def add_dir(
    tar: tarfile.TarFile,
    name: str,
    mode: int = 0o755,
    uid: int = 0,
    gid: int = 0,
):
    info = tarfile.TarInfo(
        name.lstrip("/").rstrip("/") + "/"
    )
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = uid
    info.gid = gid
    tar.addfile(info)


def add_file(
    tar: tarfile.TarFile,
    name: str,
    content: str,
    mode: int = 0o644,
    uid: int = 0,
    gid: int = 0,
):
    data = content.encode()

    info = tarfile.TarInfo(name.lstrip("/"))
    info.size = len(data)
    info.mode = mode
    info.uid = uid
    info.gid = gid

    tar.addfile(info, io.BytesIO(data))


def snapshot(
    path: Path,
    *,
    rule: str = GOOD_RULE,
    sudo_list: str = GOOD_SUDO_LIST,
    wheel_member: bool = False,
    sudoers_content: str = SUDOERS_CONTENT,
    dropin_mode: int = 0o440,
    include_dropin: bool = True,
    sudo_binary_content: str = SUDO_BINARY_CONTENT,
):
    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/etc")
        add_dir(tar, "/etc/sudoers.d")
        add_dir(tar, "/usr")
        add_dir(tar, "/usr/bin")
        add_dir(tar, "/usr/sbin")
        add_dir(tar, "/usr/local")
        add_dir(tar, "/usr/local/sbin")
        add_dir(tar, "/run")

        add_file(
            tar,
            "/etc/passwd",
            (
                "root:x:0:0:root:/root:/bin/bash\n"
                f"{USERNAME}:x:2000:2000::"
                f"/home/{USERNAME}:/bin/bash\n"
            ),
        )

        wheel_members = USERNAME if wheel_member else ""

        add_file(
            tar,
            "/etc/group",
            (
                "root:x:0:\n"
                f"wheel:x:10:{wheel_members}\n"
                f"{USERNAME}:x:2000:\n"
            ),
        )

        add_file(
            tar,
            "/etc/sudoers",
            sudoers_content,
            mode=0o440,
        )

        if include_dropin:
            add_file(
                tar,
                DROPIN,
                rule,
                mode=dropin_mode,
                uid=0,
                gid=0,
            )

        add_file(
            tar,
            HELPER,
            HELPER_CONTENT,
            mode=0o755,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            "/usr/bin/sudo",
            sudo_binary_content,
            mode=0o4755,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            "/usr/sbin/visudo",
            VISUDO_BINARY_CONTENT,
            mode=0o755,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            "/run/cyberrange-visudo.rc",
            "0\n",
        )

        add_file(
            tar,
            "/run/cyberrange-visudo.txt",
            "/etc/sudoers: parsed OK\n",
        )

        add_file(
            tar,
            "/run/cyberrange-sudo-list.rc",
            "0\n",
        )

        add_file(
            tar,
            "/run/cyberrange-sudo-list.txt",
            sudo_list,
        )


def grader_fn():
    path = LAB_DIR / "grader.py"

    spec = importlib.util.spec_from_file_location(
        "rhsa_sudo_001_test",
        path,
    )

    module = importlib.util.module_from_spec(spec)

    assert spec and spec.loader
    spec.loader.exec_module(module)

    return module.grade


def criterion(result: dict, criterion_id: str) -> dict:
    return next(
        item
        for item in result["tests"]
        if item["id"] == criterion_id
    )


class SudoGraderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text()
        )

        setup_stdout = "\n".join(
            [
                (
                    "SUDOERS_SHA256="
                    f"{sha256_text(SUDOERS_CONTENT)}"
                ),
                (
                    "HELPER_SHA256="
                    f"{sha256_text(HELPER_CONTENT)}"
                ),
                (
                    "SUDO_BINARY_SHA256="
                    f"{sha256_text(SUDO_BINARY_CONTENT)}"
                ),
                (
                    "VISUDO_BINARY_SHA256="
                    f"{sha256_text(VISUDO_BINARY_CONTENT)}"
                ),
            ]
        )

        self.context = {
            "syntax_ok": True,
            "variables": {
                "TEST_USERNAME": USERNAME,
            },
            "setup": {
                "stdout": setup_stdout,
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
        first_options: dict | None = None,
        second_options: dict | None = None,
    ):
        first_options = first_options or {}
        second_options = (
            first_options
            if second_options is None
            else second_options
        )

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"

            snapshot(first, **first_options)
            snapshot(second, **second_options)

            with SnapshotSet(
                {
                    "after_first": str(first),
                    "after_second": str(second),
                }
            ) as snaps:
                return grader_fn()(
                    self.lab,
                    self.context,
                    snaps,
                )

    def test_correct_scoped_policy_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)
        self.assertGreaterEqual(
            result["score"],
            int(self.lab["grading"]["pass_score"]),
        )

    def test_nopasswd_all_is_rejected(self):
        result = self.grade_snapshots(
            {
                "rule": BROAD_RULE,
                "sudo_list": BROAD_SUDO_LIST,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "exact_delegation",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "no_broad_privilege",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

        self.assertLess(
            result["score"],
            int(self.lab["grading"]["pass_score"]),
        )

    def test_wheel_membership_is_rejected(self):
        result = self.grade_snapshots(
            {
                "wheel_member": True,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "user_not_wheel",
            )["passed"]
        )

    def test_modified_main_sudoers_is_rejected(self):
        modified = (
            SUDOERS_CONTENT
            + "Defaults timestamp_timeout=30\n"
        )

        result = self.grade_snapshots(
            {
                "sudoers_content": modified,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "sudoers_preserved",
            )["passed"]
        )

    def test_wrong_dropin_mode_is_rejected(self):
        result = self.grade_snapshots(
            {
                "dropin_mode": 0o644,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "dropin_permissions",
            )["passed"]
        )

    def test_second_run_must_preserve_complete_state(self):
        result = self.grade_snapshots(
            {},
            {
                "dropin_mode": 0o644,
            },
        )

        self.assertTrue(
            criterion(
                result,
                "dropin_permissions",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

    def test_tampered_sudo_binary_invalidates_policy_checks(self):
        result = self.grade_snapshots(
            {
                "sudo_binary_content": "tampered-sudo\n",
            }
        )

        self.assertFalse(
            criterion(
                result,
                "visudo_valid",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "exact_delegation",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "no_broad_privilege",
            )["passed"]
        )


if __name__ == "__main__":
    unittest.main()
