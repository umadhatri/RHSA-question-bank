from __future__ import annotations

import base64
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
LAB_DIR = (
    ROOT
    / "labs"
    / "10-scheduled-jobs"
    / "RHSA-SCHED-001"
)

USERNAME = "student_123456"
UID = 2000
GID = 2000
HOME = f"/home/{USERNAME}"

HOUR = 14
MINUTE = 37

CRON_FILE = "/etc/cron.d/cyberrange-maintenance"
UNRELATED_CRON = "/etc/cron.d/cyberrange-unrelated"
CRONTAB = "/etc/crontab"
USER_CRONTAB = f"/var/spool/cron/{USERNAME}"

MAINTENANCE = "/usr/local/sbin/cyberrange-maintenance"
WEEKLY_HELPER = "/usr/local/sbin/cyberrange-weekly-audit"

EXISTING_JOB = (
    "17 3 * * 1 root "
    "/usr/local/sbin/cyberrange-weekly-audit"
)

REQUIRED_JOB = (
    f"{MINUTE} {HOUR} * * * {USERNAME} "
    "/usr/local/sbin/cyberrange-maintenance"
)

UNRELATED_JOB = (
    "23 4 * * 6 root /usr/bin/true"
)

MAINTENANCE_CONTENT = """#!/usr/bin/env bash
set -euo pipefail

printf 'daily-maintenance-ok\\n'
"""

WEEKLY_HELPER_CONTENT = """#!/usr/bin/env bash
set -euo pipefail

printf 'weekly-audit-ok\\n'
"""

CRONTAB_CONTENT = """SHELL=/bin/bash
PATH=/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=root

# synthetic system crontab
"""

UNRELATED_CRON_CONTENT = (
    f"{UNRELATED_JOB}\n"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def add_dir(
    tar: tarfile.TarFile,
    name: str,
    *,
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
    *,
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
    cron_content: str | None = None,
    cron_mode: int = 0o644,
    cron_uid: int = 0,
    cron_gid: int = 0,
    crontab_content: str = CRONTAB_CONTENT,
    unrelated_cron_content: str = UNRELATED_CRON_CONTENT,
    maintenance_content: str = MAINTENANCE_CONTENT,
    weekly_helper_content: str = WEEKLY_HELPER_CONTENT,
    user_uid: int = UID,
    user_gid: int = GID,
    user_home: str = HOME,
    user_shell: str = "/bin/bash",
    user_crontab: str | None = None,
    extra_cron_file: str | None = None,
):
    if cron_content is None:
        cron_content = (
            f"{EXISTING_JOB}\n"
            f"{REQUIRED_JOB}\n"
        )

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/etc")

        add_dir(
            tar,
            "/etc/cron.d",
            mode=0o755,
            uid=0,
            gid=0,
        )

        add_dir(tar, "/var")
        add_dir(tar, "/var/spool")

        add_dir(
            tar,
            "/var/spool/cron",
            mode=0o700,
            uid=0,
            gid=0,
        )

        add_dir(tar, "/usr")
        add_dir(tar, "/usr/local")
        add_dir(tar, "/usr/local/sbin")

        add_file(
            tar,
            "/etc/passwd",
            (
                "root:x:0:0:root:/root:/bin/bash\n"
                f"{USERNAME}:x:{user_uid}:{user_gid}::"
                f"{user_home}:{user_shell}\n"
            ),
        )

        add_file(
            tar,
            "/etc/group",
            (
                "root:x:0:\n"
                f"{USERNAME}:x:{GID}:\n"
            ),
        )

        add_file(
            tar,
            CRONTAB,
            crontab_content,
            mode=0o644,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            CRON_FILE,
            cron_content,
            mode=cron_mode,
            uid=cron_uid,
            gid=cron_gid,
        )

        add_file(
            tar,
            UNRELATED_CRON,
            unrelated_cron_content,
            mode=0o644,
            uid=0,
            gid=0,
        )

        if extra_cron_file is not None:
            add_file(
                tar,
                "/etc/cron.d/student-extra",
                extra_cron_file,
                mode=0o644,
                uid=0,
                gid=0,
            )

        if user_crontab is not None:
            add_file(
                tar,
                USER_CRONTAB,
                user_crontab,
                mode=0o600,
                uid=UID,
                gid=GID,
            )

        add_file(
            tar,
            MAINTENANCE,
            maintenance_content,
            mode=0o755,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            WEEKLY_HELPER,
            weekly_helper_content,
            mode=0o755,
            uid=0,
            gid=0,
        )


def grader_fn():
    path = LAB_DIR / "grader.py"

    spec = importlib.util.spec_from_file_location(
        "rhsa_sched_001_test",
        path,
    )

    module = importlib.util.module_from_spec(spec)

    assert spec and spec.loader
    spec.loader.exec_module(module)

    return module.grade


def criterion(
    result: dict,
    criterion_id: str,
) -> dict:
    return next(
        item
        for item in result["tests"]
        if item["id"] == criterion_id
    )


class ScheduledJobsGraderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text()
        )

        self.context = {
            "syntax_ok": True,
            "variables": {
                "TEST_USERNAME": USERNAME,
                "TEST_HOUR": HOUR,
                "TEST_MINUTE": MINUTE,
            },
            "setup": {
                "stdout": "\n".join(
                    [
                        f"EXPECTED_UID={UID}",
                        f"EXPECTED_GID={GID}",
                        f"EXPECTED_HOME={HOME}",
                        (
                            "EXISTING_JOB_B64="
                            f"{b64(EXISTING_JOB)}"
                        ),
                        (
                            "MAINTENANCE_SHA256="
                            f"{sha256_text(MAINTENANCE_CONTENT)}"
                        ),
                        (
                            "WEEKLY_HELPER_SHA256="
                            f"{sha256_text(WEEKLY_HELPER_CONTENT)}"
                        ),
                        (
                            "CRONTAB_SHA256="
                            f"{sha256_text(CRONTAB_CONTENT)}"
                        ),
                        (
                            "UNRELATED_CRON_SHA256="
                            f"{sha256_text(UNRELATED_CRON_CONTENT)}"
                        ),
                    ]
                )
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

            snapshot(
                first,
                **first_options,
            )

            snapshot(
                second,
                **second_options,
            )

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

    def test_correct_schedule_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(
            result["score"],
            100,
        )

        self.assertEqual(
            result["max_score"],
            100,
        )

    def test_overwriting_existing_job_is_rejected(self):
        result = self.grade_snapshots(
            {
                "cron_content": (
                    f"{REQUIRED_JOB}\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "existing_job_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
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
            int(
                self.lab["grading"]["pass_score"]
            ),
        )

    def test_insecure_cron_permissions_are_rejected(self):
        result = self.grade_snapshots(
            {
                "cron_mode": 0o666,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "permissions",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
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
            int(
                self.lab["grading"]["pass_score"]
            ),
        )

    def test_unauthorized_extra_job_is_rejected(self):
        result = self.grade_snapshots(
            {
                "cron_content": (
                    f"{EXISTING_JOB}\n"
                    f"{REQUIRED_JOB}\n"
                    "5 5 * * * root /usr/bin/true\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "no_extra_jobs",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
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
            int(
                self.lab["grading"]["pass_score"]
            ),
        )

    def test_global_crontab_modification_is_rejected(self):
        result = self.grade_snapshots(
            {
                "crontab_content": (
                    CRONTAB_CONTENT
                    + "\n# unauthorized change\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "cron_scope_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

    def test_unrelated_cron_file_modification_is_rejected(self):
        result = self.grade_snapshots(
            {
                "unrelated_cron_content": (
                    "0 0 * * * root /usr/bin/false\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "cron_scope_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

    def test_user_crontab_usage_is_rejected(self):
        result = self.grade_snapshots(
            {
                "user_crontab": (
                    f"{MINUTE} {HOUR} * * * "
                    f"{MAINTENANCE}\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "cron_scope_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

    def test_modified_maintenance_helper_is_rejected(self):
        result = self.grade_snapshots(
            {
                "maintenance_content": (
                    "#!/usr/bin/env bash\n"
                    "echo tampered\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "maintenance_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "schedule_integrity",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

    def test_second_run_state_drift_breaks_idempotency(self):
        result = self.grade_snapshots(
            {},
            {
                "cron_mode": 0o666,
            },
        )

        self.assertTrue(
            criterion(
                result,
                "schedule_integrity",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )


if __name__ == "__main__":
    unittest.main()
