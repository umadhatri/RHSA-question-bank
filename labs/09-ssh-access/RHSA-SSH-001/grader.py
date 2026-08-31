from __future__ import annotations

import base64
import hashlib
from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


SOURCE_KEY = "/opt/cyberrange/keys/access_key.pub"
SSHD_CONFIG = "/etc/ssh/sshd_config"
SSHD_DROPIN_DIR = "/etc/ssh/sshd_config.d"


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


def decode_setup_key(
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


def authorized_key_lines(
    snapshot: RootfsSnapshot,
    path: str,
) -> list[str]:
    text = snapshot.read_text(path) or ""

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def global_ssh_config_preserved(
    snapshot: RootfsSnapshot,
    expected_hash: str | None,
) -> bool:
    if expected_hash is None:
        return False

    if snapshot_sha256(snapshot, SSHD_CONFIG) != expected_hash:
        return False

    if not snapshot.is_dir(SSHD_DROPIN_DIR):
        return False

    if snapshot.uid(SSHD_DROPIN_DIR) != 0:
        return False

    if snapshot.gid(SSHD_DROPIN_DIR) != 0:
        return False

    if snapshot.mode(SSHD_DROPIN_DIR) != 0o700:
        return False

    dropin_files = [
        path
        for path in snapshot.paths_under(SSHD_DROPIN_DIR)
        if snapshot.is_file(path)
    ]

    return len(dropin_files) == 0


def inspect_state(
    snapshot: RootfsSnapshot,
    username: str,
    expected_uid: int | None,
    expected_gid: int | None,
    expected_home: str | None,
    existing_key: str | None,
    supplied_key: str | None,
    source_key_hash: str | None,
    sshd_config_hash: str | None,
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

    ssh_dir = (
        f"{expected_home}/.ssh"
        if expected_home is not None
        else ""
    )

    authorized_keys = (
        f"{ssh_dir}/authorized_keys"
        if ssh_dir
        else ""
    )

    ssh_directory = bool(
        ssh_dir
        and snapshot.is_dir(ssh_dir)
    )

    authorized_keys_file = bool(
        authorized_keys
        and snapshot.is_file(authorized_keys)
    )

    ownership = bool(
        ssh_directory
        and authorized_keys_file
        and expected_uid is not None
        and expected_gid is not None
        and snapshot.uid(ssh_dir) == expected_uid
        and snapshot.gid(ssh_dir) == expected_gid
        and snapshot.uid(authorized_keys) == expected_uid
        and snapshot.gid(authorized_keys) == expected_gid
    )

    permissions = bool(
        ssh_directory
        and authorized_keys_file
        and snapshot.mode(ssh_dir) == 0o700
        and snapshot.mode(authorized_keys) == 0o600
    )

    lines = (
        authorized_key_lines(
            snapshot,
            authorized_keys,
        )
        if authorized_keys_file
        else []
    )

    existing_count = (
        lines.count(existing_key.strip())
        if existing_key is not None
        else 0
    )

    supplied_count = (
        lines.count(supplied_key.strip())
        if supplied_key is not None
        else 0
    )

    existing_key_preserved = (
        existing_key is not None
        and existing_count == 1
    )

    supplied_key_installed = (
        supplied_key is not None
        and supplied_count == 1
    )

    no_extra_keys = (
        existing_key_preserved
        and supplied_key_installed
        and len(lines) == 2
    )

    source_key_preserved = (
        source_key_hash is not None
        and snapshot.is_file(SOURCE_KEY)
        and snapshot_sha256(
            snapshot,
            SOURCE_KEY,
        ) == source_key_hash
        and snapshot.uid(SOURCE_KEY) == 0
        and snapshot.gid(SOURCE_KEY) == 0
        and snapshot.mode(SOURCE_KEY) == 0o644
    )

    global_config_preserved = global_ssh_config_preserved(
        snapshot,
        sshd_config_hash,
    )

    return {
        "user_preserved": user_preserved,
        "ssh_directory": ssh_directory,
        "authorized_keys_file": authorized_keys_file,
        "ownership": ownership,
        "permissions": permissions,
        "existing_key_preserved": existing_key_preserved,
        "supplied_key_installed": supplied_key_installed,
        "no_extra_keys": no_extra_keys,
        "source_key_preserved": source_key_preserved,
        "global_config_preserved": global_config_preserved,
        "authorized_keys_bytes": (
            snapshot.read_bytes(authorized_keys)
            if authorized_keys_file
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

    existing_key = decode_setup_key(
        context,
        "EXISTING_KEY_B64",
    )

    supplied_key = decode_setup_key(
        context,
        "SUPPLIED_KEY_B64",
    )

    source_key_hash = setup_value(
        context,
        "SOURCE_KEY_SHA256",
    )

    sshd_config_hash = setup_value(
        context,
        "SSHD_CONFIG_SHA256",
    )

    first_snapshot = snapshots["after_first"]
    second_snapshot = snapshots["after_second"]

    first = inspect_state(
        first_snapshot,
        username,
        expected_uid,
        expected_gid,
        expected_home,
        existing_key,
        supplied_key,
        source_key_hash,
        sshd_config_hash,
    )

    second = inspect_state(
        second_snapshot,
        username,
        expected_uid,
        expected_gid,
        expected_home,
        existing_key,
        supplied_key,
        source_key_hash,
        sshd_config_hash,
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
        "The user account UID, GID, home directory, or shell was modified.",
    )

    book.check(
        "ssh_directory",
        first["ssh_directory"],
        "The user's .ssh directory exists.",
        "The user's .ssh directory is missing.",
    )

    book.check(
        "authorized_keys_file",
        first["authorized_keys_file"],
        "The authorized_keys file exists.",
        "The authorized_keys file is missing.",
    )

    book.check(
        "ownership",
        first["ownership"],
        "SSH files have the correct user and primary-group ownership.",
        "The .ssh directory or authorized_keys ownership is incorrect.",
    )

    book.check(
        "permissions",
        first["permissions"],
        ".ssh is 0700 and authorized_keys is 0600.",
        "SSH directory or authorized_keys permissions are insecure or incorrect.",
    )

    book.check(
        "existing_key_preserved",
        first["existing_key_preserved"],
        "The pre-existing authorized key was preserved exactly once.",
        "The pre-existing authorized key was removed or duplicated.",
    )

    book.check(
        "supplied_key_installed",
        first["supplied_key_installed"],
        "The supplied public key was installed exactly once.",
        "The supplied public key is missing or duplicated.",
    )

    book.check(
        "no_extra_keys",
        first["no_extra_keys"],
        "authorized_keys contains only the two required keys.",
        "Unexpected additional authorized keys were detected.",
    )

    book.check(
        "source_key_preserved",
        first["source_key_preserved"],
        "The supplied public-key artifact was left unchanged.",
        "The supplied public-key artifact or its protected metadata was modified.",
    )

    book.check(
        "global_config_preserved",
        first["global_config_preserved"],
        "Global SSH daemon configuration was left unchanged.",
        "Global SSH daemon configuration was modified.",
    )

    security_requirements = (
        "user_preserved",
        "ssh_directory",
        "authorized_keys_file",
        "ownership",
        "permissions",
        "existing_key_preserved",
        "supplied_key_installed",
        "no_extra_keys",
        "source_key_preserved",
        "global_config_preserved",
    )

    secure_access_state = all(
        bool(first[key])
        for key in security_requirements
    )

    book.check(
        "secure_access_state",
        secure_access_state,
        "The complete SSH access configuration satisfies all security requirements.",
        "One or more mandatory SSH access security requirements are not satisfied.",
    )

    second_rc = int(
        context.get("second_run", {}).get("returncode", 1)
    )

    second_timeout = bool(
        context.get("second_run", {}).get("timed_out", False)
    )

    required_state = (
        "user_preserved",
        "ssh_directory",
        "authorized_keys_file",
        "ownership",
        "permissions",
        "existing_key_preserved",
        "supplied_key_installed",
        "no_extra_keys",
        "source_key_preserved",
        "global_config_preserved",
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
        and first["authorized_keys_bytes"]
        == second["authorized_keys_bytes"]
    )

    book.check(
        "idempotency",
        idempotent,
        (
            "Repeated execution succeeds and preserves the "
            "complete SSH access state."
        ),
        (
            "The repeat execution did not preserve the "
            "complete required SSH access state."
        ),
    )

    return book.finalize()
