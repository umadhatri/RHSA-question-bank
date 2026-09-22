from __future__ import annotations

import hashlib
import re
from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


MAINTENANCE_COMMAND = "/usr/local/sbin/cyberrange-maintenance"


def snapshot_sha256(snapshot: RootfsSnapshot, path: str) -> str | None:
    data = snapshot.read_bytes(path)
    if data is None:
        return None
    return hashlib.sha256(data).hexdigest()


def setup_value(context: dict[str, Any], key: str) -> str | None:
    stdout = str(context.get("setup", {}).get("stdout", ""))
    prefix = f"{key}="

    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()

    return None


def read_probe_rc(snapshot: RootfsSnapshot, path: str) -> int | None:
    text = snapshot.read_text(path)

    if text is None:
        return None

    try:
        return int(text.strip())
    except ValueError:
        return None


def wheel_member(snapshot: RootfsSnapshot, username: str) -> bool:
    user = snapshot.user(username)
    wheel = snapshot.group("wheel")

    if user is None or wheel is None:
        return False

    return user.gid == wheel.gid or username in wheel.members


def active_sudoers_lines(
    snapshot: RootfsSnapshot,
) -> list[tuple[str, str]]:
    paths = ["/etc/sudoers"]

    if snapshot.is_dir("/etc/sudoers.d"):
        for path in snapshot.paths_under("/etc/sudoers.d"):
            if snapshot.is_file(path):
                paths.append(path)

    result: list[tuple[str, str]] = []

    for path in paths:
        text = snapshot.read_text(path) or ""

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            result.append((path, line))

    return result


def inspect_state(
    snapshot: RootfsSnapshot,
    username: str,
    baselines: dict[str, str | None],
) -> dict[str, Any]:
    dropin = f"/etc/sudoers.d/cyberrange-{username}"

    dropin_text = snapshot.read_text(dropin) or ""

    active_dropin_lines = [
        line.strip()
        for line in dropin_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    expected_rule = re.compile(
        rf"^{re.escape(username)}\s+"
        rf"ALL\s*=\s*\(root\)\s+"
        rf"NOPASSWD\s*:\s*"
        rf"{re.escape(MAINTENANCE_COMMAND)}\s*$"
    )

    exact_dropin = (
        len(active_dropin_lines) == 1
        and expected_rule.fullmatch(active_dropin_lines[0]) is not None
    )

    direct_user_rules: list[tuple[str, str]] = []

    user_rule_prefix = re.compile(
        rf"^{re.escape(username)}(?:\s|$)"
    )

    for path, line in active_sudoers_lines(snapshot):
        if user_rule_prefix.match(line):
            direct_user_rules.append((path, line))

    only_expected_direct_rule = (
        len(direct_user_rules) == 1
        and direct_user_rules[0][0] == dropin
        and expected_rule.fullmatch(direct_user_rules[0][1]) is not None
    )

    visudo_rc = read_probe_rc(
        snapshot,
        "/run/cyberrange-visudo.rc",
    )

    sudo_list_rc = read_probe_rc(
        snapshot,
        "/run/cyberrange-sudo-list.rc",
    )

    sudo_list_text = (
        snapshot.read_text("/run/cyberrange-sudo-list.txt")
        or ""
    )

    # sudo -l renders effective command grants as indented lines
    # beginning with a run-as specification such as:
    #
    #   (root) NOPASSWD: /usr/local/sbin/cyberrange-maintenance
    #
    grants = [
        line.strip()
        for line in sudo_list_text.splitlines()
        if line.strip().startswith("(") and ":" in line
    ]

    expected_effective_grant = re.compile(
        rf"^\(root\)\s+"
        rf"NOPASSWD\s*:\s*"
        rf"{re.escape(MAINTENANCE_COMMAND)}\s*$"
    )

    effective_policy_exact = (
        sudo_list_rc == 0
        and len(grants) == 1
        and expected_effective_grant.fullmatch(grants[0]) is not None
    )

    sudoers_preserved = (
        baselines["sudoers"] is not None
        and snapshot_sha256(snapshot, "/etc/sudoers")
        == baselines["sudoers"]
    )

    helper_preserved = (
        baselines["helper"] is not None
        and snapshot_sha256(snapshot, MAINTENANCE_COMMAND)
        == baselines["helper"]
        and snapshot.uid(MAINTENANCE_COMMAND) == 0
        and snapshot.gid(MAINTENANCE_COMMAND) == 0
        and snapshot.mode(MAINTENANCE_COMMAND) == 0o755
    )

    sudo_binary_preserved = (
        baselines["sudo_binary"] is not None
        and snapshot_sha256(snapshot, "/usr/bin/sudo")
        == baselines["sudo_binary"]
    )

    visudo_binary_preserved = (
        baselines["visudo_binary"] is not None
        and snapshot_sha256(snapshot, "/usr/sbin/visudo")
        == baselines["visudo_binary"]
    )

    trusted_tools_preserved = (
        sudo_binary_preserved
        and visudo_binary_preserved
    )

    return {
        "dropin_exists": snapshot.is_file(dropin),
        "dropin_owner": (
            snapshot.uid(dropin) == 0
            and snapshot.gid(dropin) == 0
        ),
        "dropin_permissions": snapshot.mode(dropin) == 0o440,
        "visudo_valid": (
            visudo_rc == 0
            and trusted_tools_preserved
        ),
        "exact_delegation": (
            exact_dropin
            and effective_policy_exact
            and trusted_tools_preserved
        ),
        "no_broad_privilege": (
            only_expected_direct_rule
            and effective_policy_exact
            and trusted_tools_preserved
        ),
        "user_not_wheel": not wheel_member(snapshot, username),
        "sudoers_preserved": sudoers_preserved,
        "helper_preserved": helper_preserved,
        "dropin_bytes": snapshot.read_bytes(dropin),
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    username = context["variables"]["TEST_USERNAME"]
    dropin = f"/etc/sudoers.d/cyberrange-{username}"

    baselines = {
        "sudoers": setup_value(
            context,
            "SUDOERS_SHA256",
        ),
        "helper": setup_value(
            context,
            "HELPER_SHA256",
        ),
        "sudo_binary": setup_value(
            context,
            "SUDO_BINARY_SHA256",
        ),
        "visudo_binary": setup_value(
            context,
            "VISUDO_BINARY_SHA256",
        ),
    }

    first_snapshot = snapshots["after_first"]
    second_snapshot = snapshots["after_second"]

    first = inspect_state(
        first_snapshot,
        username,
        baselines,
    )

    second = inspect_state(
        second_snapshot,
        username,
        baselines,
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
        "dropin_exists",
        first["dropin_exists"],
        f"{dropin} exists.",
        f"The required sudoers drop-in {dropin} does not exist.",
    )

    book.check(
        "dropin_owner",
        first["dropin_owner"],
        "The sudoers drop-in is owned by root:root.",
        "The sudoers drop-in must be owned by root:root.",
    )

    actual_mode = (
        first_snapshot.mode(dropin)
        if first["dropin_exists"]
        else None
    )

    mode_text = (
        f"{actual_mode:04o}"
        if actual_mode is not None
        else "missing"
    )

    book.check(
        "dropin_permissions",
        first["dropin_permissions"],
        "The sudoers drop-in mode is 0440.",
        f"Expected mode 0440; observed {mode_text}.",
    )

    book.check(
        "visudo_valid",
        first["visudo_valid"],
        "visudo accepted the complete sudo configuration.",
        "The resulting sudo configuration failed trusted visudo validation.",
    )

    book.check(
        "exact_delegation",
        first["exact_delegation"],
        (
            "The user receives passwordless sudo access to "
            "exactly the maintenance command."
        ),
        (
            "The effective sudo policy does not provide the "
            "required scoped maintenance access."
        ),
    )

    book.check(
        "no_broad_privilege",
        first["no_broad_privilege"],
        "No additional or unrestricted sudo command grant was detected.",
        "Additional or overly broad sudo privileges were detected.",
    )

    book.check(
        "user_not_wheel",
        first["user_not_wheel"],
        "The user was not added to the wheel group.",
        "The user must not receive wheel-group membership.",
    )

    book.check(
        "sudoers_preserved",
        first["sudoers_preserved"],
        "/etc/sudoers was left unchanged.",
        "/etc/sudoers was modified.",
    )

    book.check(
        "helper_preserved",
        first["helper_preserved"],
        "The protected maintenance command was left unchanged.",
        "The protected maintenance command was modified.",
    )

    second_rc = int(
        context.get("second_run", {}).get("returncode", 1)
    )

    second_timeout = bool(
        context.get("second_run", {}).get("timed_out", False)
    )

    required_state = (
        "dropin_exists",
        "dropin_owner",
        "dropin_permissions",
        "visudo_valid",
        "exact_delegation",
        "no_broad_privilege",
        "user_not_wheel",
        "sudoers_preserved",
        "helper_preserved",
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
        and first["dropin_bytes"] == second["dropin_bytes"]
    )

    book.check(
        "idempotency",
        idempotent,
        (
            "Repeated execution succeeds and preserves the "
            "complete privileged-access policy."
        ),
        (
            "The repeat execution did not preserve the "
            "complete required state."
        ),
    )

    return book.finalize()
