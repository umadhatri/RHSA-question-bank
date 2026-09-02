from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


HEADERS = (
    "[SINGLE_CHAR_LOGS]",
    "[NUMBERED_REPORTS]",
    "[BACKUPS]",
)


def expected_sections(variables: dict[str, Any]) -> dict[str, list[str]]:
    token = str(variables["TEST_TOKEN"])
    log_start = int(variables["LOG_START"])
    report_start = int(variables["REPORT_START"])

    return {
        "[SINGLE_CHAR_LOGS]": sorted(
            [
                f"app{log_start}.log",
                f"app{log_start + 1}.log",
                f"app{log_start + 2}.log",
            ]
        ),
        "[NUMBERED_REPORTS]": sorted(
            [
                f"report{report_start}.txt",
                f"report{report_start + 1}.txt",
                f"report{report_start + 2}.txt",
            ]
        ),
        "[BACKUPS]": sorted(
            [
                f"archive_{token}.old",
                f"config_{token}.old",
                f"notes_{token}.old",
            ]
        ),
    }


def expected_text(variables: dict[str, Any]) -> str:
    sections = expected_sections(variables)
    lines: list[str] = []

    for index, header in enumerate(HEADERS):
        if index:
            lines.append("")
        lines.append(header)
        lines.extend(sections[header])

    return "\n".join(lines) + "\n"


def parse_sections(text: str | None) -> dict[str, list[str]]:
    sections = {header: [] for header in HEADERS}

    if text is None:
        return sections

    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if line in HEADERS:
            current = line
            continue

        if not line:
            continue

        if current is not None:
            sections[current].append(line)

    return sections


def report_state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    output = f"/workspace/pattern_report_{token}.txt"
    text = snapshot.read_text(output)
    actual = parse_sections(text)
    expected = expected_sections(variables)

    return {
        "exists": text is not None,
        "text": text,
        "single_char_logs": actual["[SINGLE_CHAR_LOGS]"]
        == expected["[SINGLE_CHAR_LOGS]"],
        "numbered_reports": actual["[NUMBERED_REPORTS]"]
        == expected["[NUMBERED_REPORTS]"],
        "backup_files": actual["[BACKUPS]"]
        == expected["[BACKUPS]"],
        "exact_report": text == expected_text(variables),
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    variables = context["variables"]
    first = report_state(snapshots["after_first"], variables)
    second = report_state(snapshots["after_second"], variables)

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
        "The requested pattern report was created.",
        "The requested pattern report was not created.",
    )

    book.check(
        "single_char_logs",
        first["single_char_logs"],
        "The app?.log selection is correct.",
        "The single-character log selection contains missing or extra filenames.",
    )

    book.check(
        "numbered_reports",
        first["numbered_reports"],
        "The report[0-9].txt selection is correct.",
        "The numbered-report selection contains missing or extra filenames.",
    )

    book.check(
        "backup_files",
        first["backup_files"],
        "The non-hidden .old backup selection is correct.",
        "The backup selection contains missing, hidden, or incorrectly suffixed filenames.",
    )

    book.check(
        "exact_report",
        first["exact_report"],
        "The complete report has the required section order, sorting, and formatting.",
        "The report structure, ordering, formatting, or contents are not exactly correct.",
    )

    idempotent = (
        first["exact_report"]
        and second["exact_report"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["text"] == second["text"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated execution preserves the same correct report.",
        "Repeated execution changed, duplicated, appended to, or failed to preserve the report.",
    )

    return book.finalize()
