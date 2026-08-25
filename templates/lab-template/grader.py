from __future__ import annotations

from typing import Any

from grader.api import GradeBook, SnapshotSet


def grade(lab: dict[str, Any], context: dict[str, Any], snapshots: SnapshotSet) -> dict[str, Any]:
    book = GradeBook(lab)
    first = snapshots["after_first"]
    second = snapshots["after_second"]

    book.check("syntax", context.get("syntax_ok", False), "Bash syntax is valid.", "Bash syntax failed.")

    # Replace this with observable state checks against `first`.
    required_state_first = False
    required_state_second = False
    book.check("required_state", required_state_first, "Required state is correct.", "Required state is incomplete.")

    second_rc = int(context.get("second_run", {}).get("returncode", 1))
    book.check(
        "idempotency",
        required_state_first and required_state_second and second_rc == 0,
        "Repeated execution preserves the required state.",
        "Repeated execution does not preserve the required state.",
    )
    return book.finalize()
