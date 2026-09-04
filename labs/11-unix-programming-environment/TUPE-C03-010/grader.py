from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def source_spec(token: str) -> list[tuple[str, str, int]]:
    base = f"/workspace/batch_{token}"
    return [
        (
            f"{base}/alpha one.txt",
            f"alpha-{token} first\nalpha second\n",
            2,
        ),
        (
            f"{base}/beta[2].txt",
            f"beta-{token} first\nbeta second\nbeta third\n",
            3,
        ),
        (
            f"{base}/gamma*.txt",
            f"gamma-{token} only\n",
            1,
        ),
        (
            f"{base}/delta dollar$.txt",
            f"delta-{token} one\ndelta two\ndelta three\ndelta four\n",
            4,
        ),
        (
            f"{base}/epsilon-empty.txt",
            "",
            0,
        ),
        (
            f"{base}/decoy-not-supplied.txt",
            f"DECOY-{token} one\nDECOY two\nDECOY three\nDECOY four\nDECOY five\n",
            5,
        ),
    ]


def record(path: str, count: int) -> str:
    basename = path.rsplit("/", 1)[-1]
    return f"FILE={basename}\nLINES={count}\n"


def expected_short(token: str) -> str:
    sources = source_spec(token)
    return "".join(
        record(path, count)
        for path, _text, count in sources[:2]
    )


def expected_long(token: str) -> str:
    sources = source_spec(token)
    return "".join(
        record(path, count)
        for path, _text, count in sources[:5]
    )


def parse_report(text: str | None) -> list[tuple[str, int]] | None:
    if text is None:
        return None

    lines = text.splitlines()

    if len(lines) % 2 != 0:
        return None

    records: list[tuple[str, int]] = []

    for index in range(0, len(lines), 2):
        file_line = lines[index]
        count_line = lines[index + 1]

        if not file_line.startswith("FILE="):
            return None

        if not count_line.startswith("LINES="):
            return None

        try:
            count = int(count_line.split("=", 1)[1])
        except ValueError:
            return None

        records.append(
            (
                file_line.split("=", 1)[1],
                count,
            )
        )

    return records


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    sources = source_spec(token)

    short_path = f"/workspace/batch_short_{token}.txt"
    long_path = f"/workspace/batch_long_{token}.txt"

    short_text = snapshot.read_text(short_path)
    long_text = snapshot.read_text(long_path)

    short_expected = expected_short(token)
    long_expected = expected_long(token)

    short_parsed = parse_report(short_text)
    long_parsed = parse_report(long_text)

    expected_short_records = [
        (path.rsplit("/", 1)[-1], count)
        for path, _text, count in sources[:2]
    ]
    expected_long_records = [
        (path.rsplit("/", 1)[-1], count)
        for path, _text, count in sources[:5]
    ]

    counts = (
        short_parsed is not None
        and long_parsed is not None
        and sorted(count for _name, count in short_parsed)
        == sorted(count for _name, count in expected_short_records)
        and sorted(count for _name, count in long_parsed)
        == sorted(count for _name, count in expected_long_records)
    )

    order_and_quoting = (
        short_parsed == expected_short_records
        and long_parsed == expected_long_records
    )

    sources_preserved = all(
        snapshot.read_text(path) == expected_text
        and snapshot.mode(path) == 0o644
        for path, expected_text, _count in sources
    )

    return {
        "short_text": short_text,
        "long_text": long_text,
        "outputs_created": short_text is not None and long_text is not None,
        "short_batch": short_text == short_expected,
        "long_batch": long_text == long_expected,
        "counts": counts,
        "order_and_quoting": order_and_quoting,
        "sources_preserved": sources_preserved,
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    variables = context["variables"]

    first = state(
        snapshots["after_first"],
        variables,
    )
    second = state(
        snapshots["after_second"],
        variables,
    )

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
        "Both first-run batch invocations completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "outputs_created",
        first["outputs_created"],
        "Both requested batch reports were created.",
        "One or both requested batch reports were not created.",
    )

    book.check(
        "short_batch",
        first["short_batch"],
        "The two-file invocation produced the exact required report.",
        "The two-file invocation produced an incorrect report.",
    )

    book.check(
        "long_batch",
        first["long_batch"],
        "The five-file invocation produced the exact required report.",
        "The five-file invocation missed, duplicated, changed, or added a file.",
    )

    book.check(
        "counts",
        first["counts"],
        "All per-file line counts are correct in both reports.",
        "One or more per-file line counts are incorrect.",
    )

    book.check(
        "order_and_quoting",
        first["order_and_quoting"],
        "All supplied filenames were preserved literally and in argument order.",
        "A filename was split, expanded, reordered, omitted, or replaced by an unsupplied file.",
    )

    book.check(
        "sources_preserved",
        first["sources_preserved"],
        "All source and decoy files were preserved unchanged.",
        "One or more provided files were modified or had permissions changed.",
    )

    idempotent = (
        first["short_batch"]
        and first["long_batch"]
        and second["short_batch"]
        and second["long_batch"]
        and first["sources_preserved"]
        and second["sources_preserved"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["short_text"] == second["short_text"]
        and first["long_text"] == second["long_text"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated execution preserves both exact batch reports.",
        "Repeated execution changed, appended to, or failed to preserve a batch report.",
    )

    return book.finalize()
