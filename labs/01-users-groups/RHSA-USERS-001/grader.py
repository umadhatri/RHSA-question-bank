from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def required_state(snapshot: RootfsSnapshot, username: str, groupname: str) -> dict[str, bool]:
    directory = f"/srv/{groupname}"
    user = snapshot.user(username)
    group = snapshot.group(groupname)
    directory_ok = snapshot.is_dir(directory)

    membership_ok = False
    if user and group:
        membership_ok = user.gid == group.gid or username in group.members

    return {
        "group_created": group is not None,
        "user_created": user is not None,
        "bash_shell": bool(user and user.shell == "/bin/bash"),
        "group_membership": membership_ok,
        "directory_created": directory_ok,
        "directory_group": bool(directory_ok and group and snapshot.gid(directory) == group.gid),
        "permissions": bool(directory_ok and snapshot.mode(directory) == 0o2770),
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    username = context["variables"]["TEST_USERNAME"]
    groupname = context["variables"]["TEST_GROUP"]
    directory = f"/srv/{groupname}"

    first = snapshots["after_first"]
    second = snapshots["after_second"]
    first_state = required_state(first, username, groupname)
    second_state = required_state(second, username, groupname)

    book.check(
        "syntax",
        context.get("syntax_ok", False),
        "Bash syntax is valid.",
        "Bash syntax validation failed.",
    )

    first_rc = int(context.get("first_run", {}).get("returncode", 1))
    book.check(
        "first_run_exit",
        first_rc == 0 and not context.get("first_run", {}).get("timed_out", False),
        "The first execution exited successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "group_created",
        first_state["group_created"],
        "The requested group exists after the first run.",
        "The requested group was not created on the first run.",
    )
    book.check(
        "user_created",
        first_state["user_created"],
        "The requested user exists after the first run.",
        "The requested user was not created on the first run.",
    )
    book.check(
        "bash_shell",
        first_state["bash_shell"],
        "The user's login shell is /bin/bash.",
        "The user's login shell is not /bin/bash.",
    )
    book.check(
        "group_membership",
        first_state["group_membership"],
        "The user is a member of the requested group.",
        "The user is not a member of the requested group.",
    )
    book.check(
        "directory_created",
        first_state["directory_created"],
        f"{directory} exists as a directory after the first run.",
        f"{directory} was not created as a directory on the first run.",
    )
    book.check(
        "directory_group",
        first_state["directory_group"],
        "The directory has the requested group ownership.",
        "The directory group ownership is incorrect.",
    )

    actual_mode = first.mode(directory) if first_state["directory_created"] else None
    mode_text = f"{actual_mode:04o}" if actual_mode is not None else "missing"
    book.check(
        "permissions",
        first_state["permissions"],
        "The directory mode is 2770.",
        f"Expected directory mode 2770; observed {mode_text}.",
    )

    second_rc = int(context.get("second_run", {}).get("returncode", 1))
    first_complete = all(first_state.values())
    second_complete = all(second_state.values())
    idempotent = (
        first_rc == 0
        and second_rc == 0
        and not context.get("second_run", {}).get("timed_out", False)
        and first_complete
        and second_complete
    )
    if second_rc != 0 or context.get("second_run", {}).get("timed_out", False):
        failure = f"The repeat execution did not complete successfully (exit code {second_rc})."
    elif not first_complete:
        failure = "The first execution did not establish the complete required state."
    elif not second_complete:
        failure = "The repeat execution did not preserve the complete required state."
    else:
        failure = "The script did not satisfy the idempotency requirement."

    book.check(
        "idempotency",
        idempotent,
        "Repeated execution succeeds and preserves the complete required state.",
        failure,
    )

    return book.finalize()
