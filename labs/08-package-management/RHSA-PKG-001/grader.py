from __future__ import annotations

import hashlib
from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


PACKAGE_NAME = "cyberrange-monitor"
SOURCE_RPM = "/opt/cyberrange/packages/cyberrange-monitor.rpm"
EXECUTABLE = "/usr/local/bin/cyberrange-monitor"
CONFIG_FILE = "/etc/cyberrange-monitor.conf"
RPM_BINARY = "/usr/bin/rpm"


def setup_value(
    context: dict[str, Any],
    key: str,
) -> str | None:
    stdout = str(context.get("setup", {}).get("stdout", ""))
    prefix = f"{key}="

    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()

    return None


def snapshot_sha256(
    snapshot: RootfsSnapshot,
    path: str,
) -> str | None:
    data = snapshot.read_bytes(path)

    if data is None:
        return None

    return hashlib.sha256(data).hexdigest()


def read_probe_rc(
    snapshot: RootfsSnapshot,
    path: str,
) -> int | None:
    text = snapshot.read_text(path)

    if text is None:
        return None

    try:
        return int(text.strip())
    except ValueError:
        return None


def inspect_state(
    snapshot: RootfsSnapshot,
    expected: dict[str, str | None],
) -> dict[str, Any]:
    installed_rc = read_probe_rc(
        snapshot,
        "/run/cyberrange-installed-package.rc",
    )

    installed_metadata = (
        snapshot.read_text(
            "/run/cyberrange-installed-package.txt"
        )
        or ""
    ).strip()

    verify_rc = read_probe_rc(
        snapshot,
        "/run/cyberrange-rpm-verify.rc",
    )

    verify_output = (
        snapshot.read_text(
            "/run/cyberrange-rpm-verify.txt"
        )
        or ""
    ).strip()

    expected_metadata = "|".join(
        [
            PACKAGE_NAME,
            expected["version"] or "",
            expected["release"] or "",
            expected["arch"] or "",
        ]
    )

    rpm_tool_preserved = (
        expected["rpm_binary_sha256"] is not None
        and snapshot_sha256(
            snapshot,
            RPM_BINARY,
        )
        == expected["rpm_binary_sha256"]
    )

    package_installed = (
        rpm_tool_preserved
        and installed_rc == 0
        and installed_metadata.startswith(
            f"{PACKAGE_NAME}|"
        )
    )

    exact_version = (
        package_installed
        and installed_metadata == expected_metadata
    )

    executable_preserved = (
        expected["executable_sha256"] is not None
        and snapshot.is_file(EXECUTABLE)
        and snapshot_sha256(
            snapshot,
            EXECUTABLE,
        )
        == expected["executable_sha256"]
        and snapshot.mode(EXECUTABLE) == 0o755
    )

    config_preserved = (
        expected["config_sha256"] is not None
        and snapshot.is_file(CONFIG_FILE)
        and snapshot_sha256(
            snapshot,
            CONFIG_FILE,
        )
        == expected["config_sha256"]
        and snapshot.mode(CONFIG_FILE) == 0o644
    )

    rpm_verify_clean = (
        rpm_tool_preserved
        and package_installed
        and verify_rc == 0
        and verify_output == ""
    )

    source_rpm_preserved = (
        expected["source_rpm_sha256"] is not None
        and snapshot.is_file(SOURCE_RPM)
        and snapshot_sha256(
            snapshot,
            SOURCE_RPM,
        )
        == expected["source_rpm_sha256"]
        and snapshot.uid(SOURCE_RPM) == 0
        and snapshot.gid(SOURCE_RPM) == 0
        and snapshot.mode(SOURCE_RPM) == 0o644
    )

    return {
        "package_installed": package_installed,
        "exact_version": exact_version,
        "executable_preserved": executable_preserved,
        "config_preserved": config_preserved,
        "rpm_verify_clean": rpm_verify_clean,
        "source_rpm_preserved": source_rpm_preserved,
        "rpm_tool_preserved": rpm_tool_preserved,
        "installed_metadata": installed_metadata,
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    expected = {
        "version": setup_value(
            context,
            "EXPECTED_VERSION",
        ),
        "release": setup_value(
            context,
            "EXPECTED_RELEASE",
        ),
        "arch": setup_value(
            context,
            "EXPECTED_ARCH",
        ),
        "source_rpm_sha256": setup_value(
            context,
            "SOURCE_RPM_SHA256",
        ),
        "rpm_binary_sha256": setup_value(
            context,
            "RPM_BINARY_SHA256",
        ),
        "executable_sha256": setup_value(
            context,
            "EXECUTABLE_SHA256",
        ),
        "config_sha256": setup_value(
            context,
            "CONFIG_SHA256",
        ),
    }

    first_snapshot = snapshots["after_first"]
    second_snapshot = snapshots["after_second"]

    first = inspect_state(
        first_snapshot,
        expected,
    )

    second = inspect_state(
        second_snapshot,
        expected,
    )

    book.check(
        "syntax",
        context.get("syntax_ok", False),
        "Bash syntax is valid.",
        "Bash syntax validation failed.",
    )

    first_rc = int(
        context.get("first_run", {}).get("returncode", 1)
    )

    first_timeout = bool(
        context.get("first_run", {}).get("timed_out", False)
    )

    book.check(
        "first_run_exit",
        first_rc == 0 and not first_timeout,
        "The first execution exited successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "package_installed",
        first["package_installed"],
        "cyberrange-monitor is registered in the RPM database.",
        "cyberrange-monitor is not correctly registered in the RPM database.",
    )

    expected_nevra = (
        f"{PACKAGE_NAME}-"
        f"{expected['version']}-"
        f"{expected['release']}."
        f"{expected['arch']}"
    )

    book.check(
        "exact_version",
        first["exact_version"],
        f"The installed package matches {expected_nevra}.",
        (
            "The installed package version, release, or "
            "architecture does not match the supplied RPM."
        ),
    )

    book.check(
        "executable_preserved",
        first["executable_preserved"],
        "The package-managed executable is intact.",
        "The package-managed executable is missing or modified.",
    )

    book.check(
        "config_preserved",
        first["config_preserved"],
        "The package-managed configuration file is intact.",
        "The package-managed configuration file is missing or modified.",
    )

    book.check(
        "rpm_verify_clean",
        first["rpm_verify_clean"],
        "RPM verification reports no package-file changes.",
        "rpm -V detected changes or package verification failed.",
    )

    book.check(
        "source_rpm_preserved",
        first["source_rpm_preserved"],
        "The supplied RPM artifact was left unchanged.",
        "The supplied RPM artifact or its protected metadata was modified.",
    )

    book.check(
        "rpm_tool_preserved",
        first["rpm_tool_preserved"],
        "The trusted RPM tool was left unchanged.",
        "/usr/bin/rpm was modified.",
    )

    second_rc = int(
        context.get("second_run", {}).get("returncode", 1)
    )

    second_timeout = bool(
        context.get("second_run", {}).get("timed_out", False)
    )

    required_state = (
        "package_installed",
        "exact_version",
        "executable_preserved",
        "config_preserved",
        "rpm_verify_clean",
        "source_rpm_preserved",
        "rpm_tool_preserved",
    )

    first_complete = all(
        bool(first[key])
        for key in required_state
    )

    second_complete = all(
        bool(second[key])
        for key in required_state
    )

    idempotent = (
        first_rc == 0
        and second_rc == 0
        and not first_timeout
        and not second_timeout
        and first_complete
        and second_complete
        and first["installed_metadata"]
        == second["installed_metadata"]
    )

    book.check(
        "idempotency",
        idempotent,
        (
            "Repeated execution succeeds and preserves the "
            "complete package state."
        ),
        (
            "The repeat execution did not preserve the "
            "complete required package state."
        ),
    )

    return book.finalize()
