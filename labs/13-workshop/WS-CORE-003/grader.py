from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def state(snapshot: RootfsSnapshot, token: str, readme_present: bool) -> dict[str, bool]:
    project = f"/srv/project_{token}"
    readme = f"{project}/README.txt"
    archive = f"{project}/archive"
    group = snapshot.group(f"proj_{token}")
    expected_text = f"Existing project notes for {token}. Do not overwrite.\n"
    gid = group.gid if group else None
    readme_exists = snapshot.is_file(readme)
    readme_integrity = readme_exists and (not readme_present or snapshot.read_text(readme) == expected_text)
    return {
        "project_group": bool(snapshot.is_dir(project) and gid is not None and snapshot.gid(project) == gid),
        "project_mode": bool(snapshot.is_dir(project) and snapshot.mode(project) == 0o2770),
        "readme_integrity": readme_integrity,
        "readme_group": bool(snapshot.is_file(readme) and gid is not None and snapshot.gid(readme) == gid),
        "readme_mode": bool(snapshot.is_file(readme) and snapshot.mode(readme) == 0o660),
        "archive_directory": snapshot.is_dir(archive),
        "archive_policy": bool(snapshot.is_dir(archive) and gid is not None and snapshot.gid(archive) == gid and snapshot.mode(archive) == 0o2750),
    }


def grade(lab: dict[str, Any], context: dict[str, Any], snapshots: SnapshotSet) -> dict[str, Any]:
    book = GradeBook(lab)
    token = context["variables"]["TEST_TOKEN"]
    readme_present = context["variables"].get("README_PRESENT", "1") == "1"
    first = state(snapshots["after_first"], token, readme_present)
    second = state(snapshots["after_second"], token, readme_present)

    book.check("syntax", context.get("syntax_ok", False), "Bash syntax is valid.", "Bash syntax validation failed.")
    first_rc = int(context.get("first_run", {}).get("returncode", 1))
    book.check("first_run_exit", first_rc == 0 and not context.get("first_run", {}).get("timed_out", False),
               "The first execution exited successfully.", f"The first execution returned exit code {first_rc}.")
    book.check("project_group", first["project_group"], "The project directory has the required group ownership.", "Project directory group ownership is incorrect.")
    book.check("project_mode", first["project_mode"], "The project directory mode is 2770.", "The project directory mode is not 2770.")
    book.check("readme_integrity", first["readme_integrity"], "README.txt exists and any pre-existing contents were preserved.",
               "README.txt is missing or pre-existing README contents were changed.")
    book.check("readme_group", first["readme_group"], "README.txt has the required group ownership.", "README.txt group ownership is incorrect.")
    book.check("readme_mode", first["readme_mode"], "README.txt mode is 0660.", "README.txt mode is not 0660.")
    book.check("archive_directory", first["archive_directory"], "The archive directory exists.", "The archive directory was not created.")
    book.check("archive_policy", first["archive_policy"], "The archive directory has the required group ownership and mode 2750.",
               "The archive directory ownership or mode is incorrect.")

    second_rc = int(context.get("second_run", {}).get("returncode", 1))
    idem = first_rc == 0 and second_rc == 0 and all(first.values()) and all(second.values()) and not context.get("second_run", {}).get("timed_out", False)
    book.check("idempotency", idem, "Repeated execution preserves permissions and existing data.",
               "The repeat execution failed or did not preserve the complete required state.")
    return book.finalize()
