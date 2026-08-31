from __future__ import annotations

import base64
import hashlib
from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


CRON_FILE = "/etc/cron.d/cyberrange-maintenance"
UNRELATED_CRON = "/etc/cron.d/cyberrange-unrelated"
CRONTAB = "/etc/crontab"
CRON_DIR = "/etc/cron.d"
USER_CRON_DIR = "/var/spool/cron"

MAINTENANCE = "/usr/local/sbin/cyberrange-maintenance"
WEEKLY_HELPER = "/usr/local/sbin/cyberrange-weekly-audit"


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


def setup_int(
    context: dict[str, Any],
    key: str,
) -> int | None:
    value = setup_value(context, key)

    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def decode_setup_value(
    context: dict[str, Any],
    key: str,
) -> str | None:
    encoded = setup_value(context, key)

    if encoded is None:
        return None

    try:
        return base64.b64decode(encoded).decode()
    except Exception:
        return None


def snapshot_sha256(
    snapshot: RootfsSnapshot,
    path: str,
) -> str | None:
    data = snapshot.read_bytes(path)

    if data is None:
        return None

    return hashlib.sha256(data).hexdigest()


def active_lines(
    snapshot: RootfsSnapshot,
    path: str,
) -> list[str]:
    text = snapshot.read_text(path) or ""

    result: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        result.append(line)

    return result


def parse_system_cron_line(
    line: str,
) -> tuple[str, str, str, str, str, str, str] | None:
    fields = line.split(None, 6)

    if len(fields) != 7:
        return None

    return (
        fields[0],
        fields[1],
        fields[2],
        fields[3],
        fields[4],
        fields[5],
        fields[6],
    )


def required_job_matches(
    line: str,
    username: str,
    hour: int,
    minute: int,
) -> bool:
    parsed = parse_system_cron_line(line)

    if parsed is None:
        return False

    (
        actual_minute,
        actual_hour,
        day_of_month,
        month,
        day_of_week,
        actual_user,
        command,
    ) = parsed

    try:
        parsed_minute = int(actual_minute)
        parsed_hour = int(actual_hour)
    except ValueError:
        return False

    return (
        parsed_minute == minute
        and parsed_hour == hour
        and day_of_month == "*"
        and month == "*"
        and day_of_week == "*"
        and actual_user == username
        and command == MAINTENANCE
    )


def cron_scope_preserved(
    snapshot: RootfsSnapshot,
    crontab_hash: str | None,
    unrelated_hash: str | None,
) -> bool:
    if crontab_hash is None or unrelated_hash is None:
        return False

    if snapshot_sha256(snapshot, CRONTAB) != crontab_hash:
        return False

    if not snapshot.is_file(UNRELATED_CRON):
        return False

    if snapshot_sha256(snapshot, UNRELATED_CRON) != unrelated_hash:
        return False

    if snapshot.uid(UNRELATED_CRON) != 0:
        return False

    if snapshot.gid(UNRELATED_CRON) != 0:
        return False

    if snapshot.mode(UNRELATED_CRON) != 0o644:
        return False

    if not snapshot.is_dir(CRON_DIR):
        return False

    cron_files = sorted(
        path
        for path in snapshot.paths_under(CRON_DIR)
        if snapshot.is_file(path)
    )

    expected_cron_files = sorted(
        [
            CRON_FILE,
            UNRELATED_CRON,
        ]
    )

    if cron_files != expected_cron_files:
        return False

    if not snapshot.is_dir(USER_CRON_DIR):
        return False

    user_cron_files = [
        path
        for path in snapshot.paths_under(USER_CRON_DIR)
        if snapshot.is_file(path)
    ]

    return len(user_cron_files) == 0


def inspect_state(
    snapshot: RootfsSnapshot,
    username: str,
    hour: int,
    minute: int,
    expected_uid: int | None,
    expected_gid: int | None,
    expected_home: str | None,
    existing_job: str | None,
    maintenance_hash: str | None,
    weekly_helper_hash: str | None,
    crontab_hash: str | None,
    unrelated_hash: str | None,
) -> dict[str, Any]:
    user = snapshot.user(username)

    user_preserved = (
        user is not None
        and expected_uid is not None
        and expected_gid is not None
        and expected_home is not None
        and user.uid == expected_uid
        and user.gid == expected_gid
        and user.home == expected_home
        and user.shell == "/bin/bash"
    )

    cron_file_exists = snapshot.is_file(CRON_FILE)

    ownership = bool(
        cron_file_exists
        and snapshot.uid(CRON_FILE) == 0
        and snapshot.gid(CRON_FILE) == 0
    )

    permissions = bool(
        cron_file_exists
        and snapshot.mode(CRON_FILE) == 0o644
    )

    lines = (
        active_lines(snapshot, CRON_FILE)
        if cron_file_exists
        else []
    )

    existing_job_preserved = bool(
        existing_job is not None
        and lines.count(existing_job.strip()) == 1
    )

    required_matches = [
        line
        for line in lines
        if required_job_matches(
            line,
            username,
            hour,
            minute,
        )
    ]

    required_job_scheduled = len(required_matches) == 1

    no_extra_jobs = (
        existing_job_preserved
        and required_job_scheduled
        and len(lines) == 2
    )

    maintenance_preserved = (
        maintenance_hash is not None
        and snapshot.is_file(MAINTENANCE)
        and snapshot_sha256(
            snapshot,
            MAINTENANCE,
        ) == maintenance_hash
        and snapshot.uid(MAINTENANCE) == 0
        and snapshot.gid(MAINTENANCE) == 0
        and snapshot.mode(MAINTENANCE) == 0o755
    )

    weekly_helper_preserved = (
        weekly_helper_hash is not None
        and snapshot.is_file(WEEKLY_HELPER)
        and snapshot_sha256(
            snapshot,
            WEEKLY_HELPER,
        ) == weekly_helper_hash
        and snapshot.uid(WEEKLY_HELPER) == 0
        and snapshot.gid(WEEKLY_HELPER) == 0
        and snapshot.mode(WEEKLY_HELPER) == 0o755
    )

    scope_preserved = cron_scope_preserved(
        snapshot,
        crontab_hash,
        unrelated_hash,
    )

    return {
        "user_preserved": user_preserved,
        "cron_file_exists": cron_file_exists,
        "ownership": ownership,
        "permissions": permissions,
        "existing_job_preserved": existing_job_preserved,
        "required_job_scheduled": required_job_scheduled,
        "no_extra_jobs": no_extra_jobs,
        "maintenance_preserved": maintenance_preserved,
        "weekly_helper_preserved": weekly_helper_preserved,
        "cron_scope_preserved": scope_preserved,
        "cron_file_bytes": (
            snapshot.read_bytes(CRON_FILE)
            if cron_file_exists
            else None
        ),
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    username = context["variables"]["TEST_USERNAME"]
    hour = int(context["variables"]["TEST_HOUR"])
    minute = int(context["variables"]["TEST_MINUTE"])

    expected_uid = setup_int(
        context,
        "EXPECTED_UID",
    )

    expected_gid = setup_int(
        context,
        "EXPECTED_GID",
    )

    expected_home = setup_value(
        context,
        "EXPECTED_HOME",
    )

    existing_job = decode_setup_value(
        context,
        "EXISTING_JOB_B64",
    )

    maintenance_hash = setup_value(
        context,
        "MAINTENANCE_SHA256",
    )

    weekly_helper_hash = setup_value(
        context,
        "WEEKLY_HELPER_SHA256",
    )

    crontab_hash = setup_value(
        context,
        "CRONTAB_SHA256",
    )

    unrelated_hash = setup_value(
        context,
        "UNRELATED_CRON_SHA256",
    )

    first_snapshot = snapshots["after_first"]
    second_snapshot = snapshots["after_second"]

    first = inspect_state(
        first_snapshot,
        username,
        hour,
        minute,
        expected_uid,
        expected_gid,
        expected_home,
        existing_job,
        maintenance_hash,
        weekly_helper_hash,
        crontab_hash,
        unrelated_hash,
    )

    second = inspect_state(
        second_snapshot,
        username,
        hour,
        minute,
        expected_uid,
        expected_gid,
        expected_home,
        existing_job,
        maintenance_hash,
        weekly_helper_hash,
        crontab_hash,
        unrelated_hash,
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
        "user_preserved",
        first["user_preserved"],
        "The original user account was preserved.",
        "The scheduled user's UID, GID, home directory, or shell was modified.",
    )

    book.check(
        "cron_file_exists",
        first["cron_file_exists"],
        f"{CRON_FILE} exists.",
        f"The required cron file {CRON_FILE} is missing.",
    )

    book.check(
        "ownership",
        first["ownership"],
        "The managed cron file is owned by root:root.",
        "The managed cron file ownership is incorrect.",
    )

    book.check(
        "permissions",
        first["permissions"],
        "The managed cron file mode is 0644.",
        "The managed cron file mode must be 0644.",
    )

    book.check(
        "existing_job_preserved",
        first["existing_job_preserved"],
        "The existing weekly audit job was preserved exactly once.",
        "The existing weekly audit job was removed, changed, or duplicated.",
    )

    book.check(
        "required_job_scheduled",
        first["required_job_scheduled"],
        (
            f"The maintenance command is scheduled daily at "
            f"{hour:02d}:{minute:02d} as {username}."
        ),
        (
            "The required maintenance job has the wrong time, "
            "user, command, or multiplicity."
        ),
    )

    book.check(
        "no_extra_jobs",
        first["no_extra_jobs"],
        "The managed cron file contains only the two required jobs.",
        "Unexpected additional jobs were detected in the managed cron file.",
    )

    book.check(
        "maintenance_preserved",
        first["maintenance_preserved"],
        "The daily maintenance command was left unchanged.",
        "The daily maintenance command or its protected metadata was modified.",
    )

    book.check(
        "weekly_helper_preserved",
        first["weekly_helper_preserved"],
        "The weekly audit command was left unchanged.",
        "The weekly audit command or its protected metadata was modified.",
    )

    book.check(
        "cron_scope_preserved",
        first["cron_scope_preserved"],
        "Unrelated cron configuration and user crontabs were left unchanged.",
        (
            "Unrelated cron configuration was modified, "
            "an extra cron.d file was created, or a user crontab was used."
        ),
    )

    integrity_requirements = (
        "user_preserved",
        "cron_file_exists",
        "ownership",
        "permissions",
        "existing_job_preserved",
        "required_job_scheduled",
        "no_extra_jobs",
        "maintenance_preserved",
        "weekly_helper_preserved",
        "cron_scope_preserved",
    )

    schedule_integrity = all(
        bool(first[key])
        for key in integrity_requirements
    )

    book.check(
        "schedule_integrity",
        schedule_integrity,
        (
            "The complete scheduled-maintenance configuration "
            "satisfies all integrity requirements."
        ),
        (
            "One or more mandatory scheduling integrity "
            "requirements are not satisfied."
        ),
    )

    second_rc = int(
        context.get("second_run", {}).get("returncode", 1)
    )

    second_timeout = bool(
        context.get("second_run", {}).get("timed_out", False)
    )

    first_complete = all(
        bool(first[key])
        for key in integrity_requirements
    )

    second_complete = all(
        bool(second[key])
        for key in integrity_requirements
    )

    idempotent = (
        first_rc == 0
        and second_rc == 0
        and not first_timeout
        and not second_timeout
        and first_complete
        and second_complete
        and first["cron_file_bytes"]
        == second["cron_file_bytes"]
    )

    book.check(
        "idempotency",
        idempotent,
        (
            "Repeated execution succeeds and preserves the "
            "complete scheduled-maintenance state."
        ),
        (
            "The repeat execution did not preserve the "
            "complete required scheduling state."
        ),
    )

    return book.finalize()
