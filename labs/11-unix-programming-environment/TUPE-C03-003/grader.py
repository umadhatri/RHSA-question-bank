from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def expected_label(token: str) -> str:
    return f"Batch  {token}  *  ?  semi;colon"


def expected_values(token: str) -> dict[str, str]:
    return {
        "customer": f"Customer record {token} with spaces",
        "price": f"Price tier {token} dollar-four",
        "pattern": f"Pattern literal {token} star",
        "question": f"Question literal {token} mark",
    }


def expected_text(token: str) -> str:
    values = expected_values(token)

    return (
        "[LABEL]\n"
        f"{expected_label(token)}\n"
        "\n"
        "[FILES]\n"
        f"customer={values['customer']}\n"
        f"price={values['price']}\n"
        f"pattern={values['pattern']}\n"
        f"question={values['question']}\n"
    )


def parse_report(text: str | None) -> dict[str, Any]:
    if text is None:
        return {
            "label": None,
            "values": {},
        }

    lines = text.splitlines()
    label: str | None = None
    values: dict[str, str] = {}

    try:
        label_index = lines.index("[LABEL]")
    except ValueError:
        label_index = -1

    if label_index >= 0 and label_index + 1 < len(lines):
        label = lines[label_index + 1]

    try:
        files_index = lines.index("[FILES]")
    except ValueError:
        files_index = -1

    if files_index >= 0:
        for line in lines[files_index + 1:]:
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in {"customer", "price", "pattern", "question"}:
                values[key] = value

    return {
        "label": label,
        "values": values,
    }


def report_state(snapshot: RootfsSnapshot, token: str) -> dict[str, Any]:
    output = f"/workspace/quote report {token} ?.txt"
    text = snapshot.read_text(output)
    parsed = parse_report(text)
    values = expected_values(token)

    return {
        "exists": text is not None,
        "text": text,
        "label_preserved": parsed["label"] == expected_label(token),
        "special_file_values": parsed["values"] == values,
        "exact_report": text == expected_text(token),
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    token = str(context["variables"]["TEST_TOKEN"])
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
        "The requested quoting report was created.",
        "The requested quoting report was not created at the exact output path.",
    )

    book.check(
        "label_preserved",
        first["label_preserved"],
        "The label argument was preserved exactly, including spaces and metacharacters.",
        "The label argument was changed by word splitting, expansion, or incorrect formatting.",
    )

    book.check(
        "special_file_values",
        first["special_file_values"],
        "The exact files containing spaces and metacharacters were read correctly.",
        "One or more special-character filenames were misread, expanded, or replaced by a decoy.",
    )

    book.check(
        "exact_report",
        first["exact_report"],
        "The complete report matches the required structure and contents.",
        "The report structure or contents are not exactly correct.",
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
