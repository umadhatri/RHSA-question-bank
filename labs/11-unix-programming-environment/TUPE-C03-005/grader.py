from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def expected_items(token: str) -> list[str]:
    return [
        f"alpha-{token}",
        f"beta-{token}",
        f"gamma-{token}",
        f"delta-{token}",
    ]


def manifest_text(label: str, items: list[str]) -> str:
    lines = [
        f"LABEL={label}",
        f"COUNT={len(items)}",
    ]

    lines.extend(
        f"{index}={item}"
        for index, item in enumerate(items, start=1)
    )

    return "\n".join(lines) + "\n"


def parse_manifest(text: str | None) -> dict[str, Any] | None:
    if text is None:
        return None

    lines = text.splitlines()

    if len(lines) < 3:
        return None

    if not lines[0].startswith("LABEL="):
        return None

    if not lines[1].startswith("COUNT="):
        return None

    label = lines[0].split("=", 1)[1]

    try:
        count = int(lines[1].split("=", 1)[1])
    except ValueError:
        return None

    items: list[str] = []

    for expected_index, line in enumerate(lines[2:], start=1):
        prefix = f"{expected_index}="

        if not line.startswith(prefix):
            return None

        items.append(line[len(prefix):])

    return {
        "label": label,
        "count": count,
        "items": items,
    }


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    items = expected_items(token)

    short_path = f"/workspace/short_manifest_{token}.txt"
    long_path = f"/workspace/long_manifest_{token}.txt"

    short_text = snapshot.read_text(short_path)
    long_text = snapshot.read_text(long_path)

    expected_short = manifest_text(
        f"short-{token}",
        items[:2],
    )
    expected_long = manifest_text(
        f"long-{token}",
        items,
    )

    short_parsed = parse_manifest(short_text)
    long_parsed = parse_manifest(long_text)

    outputs_created = (
        short_text is not None
        and long_text is not None
    )

    labels_and_counts = (
        short_parsed is not None
        and long_parsed is not None
        and short_parsed["label"] == f"short-{token}"
        and long_parsed["label"] == f"long-{token}"
        and short_parsed["count"] == 2
        and long_parsed["count"] == 4
    )

    argument_order = (
        short_parsed is not None
        and long_parsed is not None
        and short_parsed["items"] == items[:2]
        and long_parsed["items"] == items
    )

    return {
        "short_text": short_text,
        "long_text": long_text,
        "outputs_created": outputs_created,
        "short_manifest": short_text == expected_short,
        "long_manifest": long_text == expected_long,
        "labels_and_counts": labels_and_counts,
        "argument_order": argument_order,
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
        "The first execution completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "outputs_created",
        first["outputs_created"],
        "Both requested manifest files were created.",
        "One or both requested manifest files were not created.",
    )

    book.check(
        "short_manifest",
        first["short_manifest"],
        "The two-item invocation produced the exact required manifest.",
        "The two-item invocation produced an incorrect manifest.",
    )

    book.check(
        "long_manifest",
        first["long_manifest"],
        "The four-item invocation produced the exact required manifest.",
        "The four-item invocation produced an incorrect manifest.",
    )

    book.check(
        "labels_and_counts",
        first["labels_and_counts"],
        "Labels and item counts are correct for both invocation sizes.",
        "A label or item count is incorrect for one or both invocations.",
    )

    book.check(
        "argument_order",
        first["argument_order"],
        "All item arguments were preserved in their original order.",
        "One or more item arguments were missing, reordered, or changed.",
    )

    idempotent = (
        first["short_manifest"]
        and first["long_manifest"]
        and second["short_manifest"]
        and second["long_manifest"]
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
        "Repeated execution preserves both correct manifests.",
        "Repeated execution changed, duplicated, appended to, or failed to preserve a manifest.",
    )

    return book.finalize()
