from __future__ import annotations

from typing import Any

from grader.api import GradeBook, SnapshotSet


def parse_report(text: str | None) -> tuple[bool, list[tuple[int, str]]]:
    if text is None:
        return False, []
    rows: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 2:
            return False, rows
        try:
            count = int(parts[0])
        except ValueError:
            return False, rows
        rows.append((count, parts[1]))
    return True, rows


def grade(lab: dict[str, Any], context: dict[str, Any], snapshots: SnapshotSet) -> dict[str, Any]:
    book = GradeBook(lab)
    v = context["variables"]
    output = f"/workspace/failed_logins_{v['TEST_TOKEN']}.txt"
    expected_counts = {v["IP_A"]: int(v["COUNT_A"]), v["IP_B"]: int(v["COUNT_B"]), v["IP_C"]: int(v["COUNT_C"])}
    expected_rows = sorted(((count, ip) for ip, count in expected_counts.items()), key=lambda x: (-x[0], x[1]))

    first_text = snapshots["after_first"].read_text(output)
    second_text = snapshots["after_second"].read_text(output)
    fmt_ok, rows = parse_report(first_text)
    ips = [ip for _, ip in rows]
    row_map = {ip: count for count, ip in rows}

    book.check("syntax", context.get("syntax_ok", False), "Bash syntax is valid.", "Bash syntax validation failed.")
    first_rc = int(context.get("first_run", {}).get("returncode", 1))
    book.check("first_run_exit", first_rc == 0 and not context.get("first_run", {}).get("timed_out", False),
               "The first execution exited successfully.", f"The first execution returned exit code {first_rc}.")
    book.check("output_created", first_text is not None, "The requested output report was created.", "The requested output report was not created.")
    book.check("output_format", fmt_ok and len(rows) == 3, "Every report row uses the required 'COUNT IP_ADDRESS' format.",
               "The report does not contain exactly three well-formed 'COUNT IP_ADDRESS' rows.")
    book.check("ip_set", set(ips) == set(expected_counts), "The report contains exactly the IPs with failed-password events.",
               "The report is missing a failed-login IP or includes an unrelated IP.")
    correct_counts = sum(1 for ip, expected in expected_counts.items() if row_map.get(ip) == expected)
    book.award("counts", round(25 * correct_counts / 3), correct_counts == 3,
               f"Correct failed-login count for {correct_counts} of 3 source IPs.")
    book.check("descending_order", rows == expected_rows, "Rows are sorted by descending count with the required tie-breaker.",
               "Rows are not in the required descending-count order.")
    book.check("no_duplicates", len(ips) == len(set(ips)), "No duplicate IP rows are present.", "The report contains duplicate IP rows.")

    second_rc = int(context.get("second_run", {}).get("returncode", 1))
    exact_first = fmt_ok and rows == expected_rows
    idem = first_rc == 0 and second_rc == 0 and exact_first and second_text == first_text and not context.get("second_run", {}).get("timed_out", False)
    book.check("idempotency", idem, "Repeated execution overwrites the report and preserves the exact correct output.",
               "The repeat execution failed, appended duplicate output, or changed the required report.")
    return book.finalize()
