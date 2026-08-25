from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def expected(token: str) -> dict[str, list[str]]:
    return {
        "text": [f"report_{token}.txt", f"notes_{token}.txt"],
        "logs": [f"server_{token}.log", f"audit_{token}.log"],
        "other": [f"payload_{token}.bin", f"config_{token}.conf", f".environment_{token}"],
    }


def state(snapshot: RootfsSnapshot, token: str) -> dict[str, bool]:
    src = f"/workspace/source_{token}"
    dst = f"/workspace/destination_{token}"
    exp = expected(token)
    category_dirs = all(snapshot.is_dir(f"{dst}/{cat}") for cat in exp)
    category_ok = {
        cat: all(snapshot.is_file(f"{dst}/{cat}/{name}") for name in names)
        for cat, names in exp.items()
    }
    source_cleared = all(
        not snapshot.is_file(f"{src}/{name}")
        for names in exp.values() for name in names
    )
    source_directories_preserved = snapshot.is_dir(f"{src}/leave_this_directory")
    return {
        "category_directories": category_dirs,
        "text_files": category_ok["text"],
        "log_files": category_ok["logs"],
        "other_files": category_ok["other"],
        "source_cleared": source_cleared,
        "source_directories_preserved": source_directories_preserved,
    }


def grade(lab: dict[str, Any], context: dict[str, Any], snapshots: SnapshotSet) -> dict[str, Any]:
    book = GradeBook(lab)
    token = context["variables"]["TEST_TOKEN"]
    first = state(snapshots["after_first"], token)
    second = state(snapshots["after_second"], token)

    book.check("syntax", context.get("syntax_ok", False), "Bash syntax is valid.", "Bash syntax validation failed.")
    first_rc = int(context.get("first_run", {}).get("returncode", 1))
    book.check("first_run_exit", first_rc == 0 and not context.get("first_run", {}).get("timed_out", False),
               "The first execution exited successfully.", f"The first execution returned exit code {first_rc}.")
    book.check("category_directories", first["category_directories"], "text, logs, and other directories were created.",
               "One or more required category directories are missing.")
    book.check("text_files", first["text_files"], "All .txt files were moved to text/.", "The .txt files were not organized correctly.")
    book.check("log_files", first["log_files"], "All .log files were moved to logs/.", "The .log files were not organized correctly.")
    book.check("other_files", first["other_files"], "All remaining regular files, including the hidden file, were moved to other/.",
               "One or more non-text/non-log files were not moved to other/.")
    book.check("source_cleared", first["source_cleared"], "No graded regular files remain at the top level of the source directory.",
               "One or more graded regular files remain in the source directory.")
    book.check("source_directories_preserved", first["source_directories_preserved"], "Existing source subdirectories were left in place.",
               "A source subdirectory was moved or removed even though only regular files should be organized.")

    second_rc = int(context.get("second_run", {}).get("returncode", 1))
    complete_first = all(first.values())
    complete_second = all(second.values())
    idem = first_rc == 0 and second_rc == 0 and complete_first and complete_second and not context.get("second_run", {}).get("timed_out", False)
    book.check("idempotency", idem, "Repeated execution succeeds and preserves the complete organization.",
               "The repeat execution failed or did not preserve the complete required state.")
    return book.finalize()
