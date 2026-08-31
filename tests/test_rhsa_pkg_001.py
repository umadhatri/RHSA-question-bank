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
LAB_DIR = (
    ROOT
    / "labs"
    / "08-package-management"
    / "RHSA-PKG-001"
)

PACKAGE_NAME = "cyberrange-monitor"
VERSION = "1.555.0"
RELEASE = "1"
ARCH = "noarch"

SOURCE_RPM = "/opt/cyberrange/packages/cyberrange-monitor.rpm"
EXECUTABLE = "/usr/local/bin/cyberrange-monitor"
CONFIG = "/etc/cyberrange-monitor.conf"
RPM_BINARY = "/usr/bin/rpm"

SOURCE_RPM_CONTENT = "synthetic-rpm-fixture\n"
EXECUTABLE_CONTENT = (
    "#!/usr/bin/bash\n"
    "printf 'cyberrange-monitor-ok\\n'\n"
)
CONFIG_CONTENT = (
    "enabled=true\n"
    "interval=30\n"
)
RPM_BINARY_CONTENT = "synthetic-rpm-binary\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def add_dir(
    tar: tarfile.TarFile,
    name: str,
    mode: int = 0o755,
):
    info = tarfile.TarInfo(
        name.lstrip("/").rstrip("/") + "/"
    )
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = 0
    info.gid = 0
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
    installed_rc: int = 0,
    metadata: str | None = None,
    verify_rc: int = 0,
    verify_output: str = "",
    executable_content: str = EXECUTABLE_CONTENT,
    config_content: str = CONFIG_CONTENT,
    source_rpm_content: str = SOURCE_RPM_CONTENT,
    rpm_binary_content: str = RPM_BINARY_CONTENT,
):
    if metadata is None:
        metadata = (
            f"{PACKAGE_NAME}|{VERSION}|{RELEASE}|{ARCH}"
        )

    with tarfile.open(path, "w") as tar:
        for directory in (
            "/run",
            "/opt",
            "/opt/cyberrange",
            "/opt/cyberrange/packages",
            "/usr",
            "/usr/bin",
            "/usr/local",
            "/usr/local/bin",
            "/etc",
        ):
            add_dir(tar, directory)

        add_file(
            tar,
            SOURCE_RPM,
            source_rpm_content,
            mode=0o644,
        )

        add_file(
            tar,
            RPM_BINARY,
            rpm_binary_content,
            mode=0o755,
        )

        add_file(
            tar,
            EXECUTABLE,
            executable_content,
            mode=0o755,
        )

        add_file(
            tar,
            CONFIG,
            config_content,
            mode=0o644,
        )

        add_file(
            tar,
            "/run/cyberrange-installed-package.rc",
            f"{installed_rc}\n",
        )

        add_file(
            tar,
            "/run/cyberrange-installed-package.txt",
            metadata + "\n",
        )

        add_file(
            tar,
            "/run/cyberrange-rpm-verify.rc",
            f"{verify_rc}\n",
        )

        add_file(
            tar,
            "/run/cyberrange-rpm-verify.txt",
            verify_output,
        )


def grader_fn():
    path = LAB_DIR / "grader.py"

    spec = importlib.util.spec_from_file_location(
        "rhsa_pkg_001_test",
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


class PackageManagementGraderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text()
        )

        self.context = {
            "syntax_ok": True,
            "setup": {
                "stdout": "\n".join(
                    [
                        f"EXPECTED_VERSION={VERSION}",
                        f"EXPECTED_RELEASE={RELEASE}",
                        f"EXPECTED_ARCH={ARCH}",
                        (
                            "SOURCE_RPM_SHA256="
                            f"{sha256_text(SOURCE_RPM_CONTENT)}"
                        ),
                        (
                            "RPM_BINARY_SHA256="
                            f"{sha256_text(RPM_BINARY_CONTENT)}"
                        ),
                        (
                            "EXECUTABLE_SHA256="
                            f"{sha256_text(EXECUTABLE_CONTENT)}"
                        ),
                        (
                            "CONFIG_SHA256="
                            f"{sha256_text(CONFIG_CONTENT)}"
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

    def test_correct_package_state_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_fake_file_copy_without_rpm_install_is_rejected(self):
        result = self.grade_snapshots(
            {
                "installed_rc": 1,
                "metadata": (
                    "package cyberrange-monitor "
                    "is not installed"
                ),
                "verify_rc": 1,
                "verify_output": (
                    "package cyberrange-monitor "
                    "is not installed\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "package_installed",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "exact_version",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "rpm_verify_clean",
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

    def test_modified_config_is_rejected(self):
        result = self.grade_snapshots(
            {
                "config_content": (
                    "enabled=false\n"
                    "interval=999\n"
                ),
                "verify_rc": 1,
                "verify_output": (
                    "S.5....T.  c "
                    "/etc/cyberrange-monitor.conf\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "config_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "rpm_verify_clean",
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

    def test_wrong_installed_version_is_rejected(self):
        result = self.grade_snapshots(
            {
                "metadata": (
                    f"{PACKAGE_NAME}|1.999.0|"
                    f"{RELEASE}|{ARCH}"
                ),
            }
        )

        self.assertTrue(
            criterion(
                result,
                "package_installed",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "exact_version",
            )["passed"]
        )

    def test_modified_executable_is_rejected(self):
        result = self.grade_snapshots(
            {
                "executable_content": (
                    "#!/usr/bin/bash\n"
                    "echo tampered\n"
                ),
                "verify_rc": 1,
                "verify_output": (
                    "S.5....T.    "
                    "/usr/local/bin/cyberrange-monitor\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "executable_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "rpm_verify_clean",
            )["passed"]
        )

    def test_modified_source_rpm_is_rejected(self):
        result = self.grade_snapshots(
            {
                "source_rpm_content": "tampered-rpm\n",
            }
        )

        self.assertFalse(
            criterion(
                result,
                "source_rpm_preserved",
            )["passed"]
        )

    def test_tampered_rpm_binary_invalidates_package_checks(self):
        result = self.grade_snapshots(
            {
                "rpm_binary_content": "tampered-rpm-tool\n",
            }
        )

        self.assertFalse(
            criterion(
                result,
                "rpm_tool_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "package_installed",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "exact_version",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "rpm_verify_clean",
            )["passed"]
        )

    def test_second_run_must_preserve_complete_package_state(self):
        result = self.grade_snapshots(
            {},
            {
                "config_content": "enabled=false\n",
                "verify_rc": 1,
                "verify_output": (
                    "S.5....T.  c "
                    "/etc/cyberrange-monitor.conf\n"
                ),
            },
        )

        self.assertTrue(
            criterion(
                result,
                "config_preserved",
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
