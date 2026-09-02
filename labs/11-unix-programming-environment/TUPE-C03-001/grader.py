from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def expected_lines(token: str) -> list[str]:
    return sorted(
        {
            f"ERROR alpha-{token} disk-threshold",
            f"ERROR beta-{token} queue-backlog",
            f"ERROR shared-{token} authentication-retry",
            f"ERROR zeta-{token} service-unavailable",
        }
    )


def report_state(snapshot: RootfsSnapshot, token: str) -> dict[str, Any]:
    path = f"/workspace/error_report_{token}.txt"
    text = snapshot.read_text(path)

    if text is None:
        return {
            "exists": False,
            "text": None,
            "lines": [],
            "only_errors": False,
            "both_sources": False,
            "exact": False,
        }

    lines = text.splitlines()
    expected = expected_lines(token)

    source_a_record = f"ERROR alpha-{token} disk-threshold"
    source_b_record = f"ERROR beta-{token} queue-backlog"

    return {
        "exists": True,
        "text": text,
        "lines": lines,
        "only_errors": bool(lines)
        and all(line.startswith("ERROR ") for line in lines),
        "both_sources": (
            source_a_record in lines
            and source_b_record in lines
        ),
        "exact": lines == expected,
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    token = context["variables"]["TEST_TOKEN"]
    first = report_state(snapshots["after_first"], token)
    second = report_state(snapshots["after_second"], token)

    first_run = context.get("first_run", {})
    second_run = context.get("second_run", {})

    first_rc = int(first_run.get("returncode", 1))
    second_rc = int(second_run.get("returncode", 1))

    book.check(
        "syntax",
        context.get("syntax_ok", False),
        "Bash syntax is valid.",
        "Bash syntax validation failed.",
    )

    book.check(
        "first_run_exit",
        first_rc == 0 and not first_run.get("timed_out", False),
        "The first execution exited successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "output_created",
        first["exists"],
        "The requested report file was created.",
        "The requested report file was not created.",
    )

    book.check(
        "error_filtering",
        first["only_errors"],
        "The report contains only records beginning exactly with 'ERROR '.",
        "The report contains non-error, stale, or incorrectly filtered records.",
    )

    book.check(
        "both_sources",
        first["both_sources"],
        "Error records from both source commands are represented.",
        "The report is missing required error output from one or both source commands.",
    )

    book.check(
        "sorted_unique_report",
        first["exact"],
        "The report contains the complete sorted set of unique error records.",
        "The report is incomplete, unsorted, duplicated, or contains unexpected records.",
    )

    idempotent = (
        first["exact"]
        and second["exact"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["text"] == second["text"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated execution replaces the report and preserves the correct result.",
        "Repeated execution changed, duplicated, appended to, or failed to preserve the report.",
    )

    return book.finalize()
