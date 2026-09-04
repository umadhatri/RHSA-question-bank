from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def dynamic_value(token: str, build: int, prefix: str) -> str:
    return f"{prefix}-{token} build-{build} [ready] $literal *"


def producer_text(token: str, build: int, prefix: str) -> str:
    value = dynamic_value(token, build, prefix)
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' '{value}'\n"
    )


def formatter_text() -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        "[[ $# -eq 1 ]] || {\n"
        "    printf 'expected exactly one argument, got %d\\n' \"$#\" >&2\n"
        "    exit 23\n"
        "}\n"
        "\n"
        "printf 'CAPTURED=%s\\n' \"$1\"\n"
    )


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    build_a = int(variables["BUILD_A"])
    build_b = int(variables["BUILD_B"])

    output_a = f"/workspace/dynamic_a_{token}.txt"
    output_b = f"/workspace/dynamic_b_{token}.txt"
    producer_a = f"/workspace/producer_a_{token}"
    producer_b = f"/workspace/producer_b_{token}"
    formatter = f"/workspace/formatter_{token}"

    value_a = dynamic_value(token, build_a, "alpha")
    value_b = dynamic_value(token, build_b, "beta")

    expected_a = f"CAPTURED={value_a}\n"
    expected_b = f"CAPTURED={value_b}\n"

    text_a = snapshot.read_text(output_a)
    text_b = snapshot.read_text(output_b)

    helpers_preserved = (
        snapshot.read_text(producer_a)
        == producer_text(token, build_a, "alpha")
        and snapshot.read_text(producer_b)
        == producer_text(token, build_b, "beta")
        and snapshot.read_text(formatter) == formatter_text()
        and snapshot.mode(producer_a) == 0o755
        and snapshot.mode(producer_b) == 0o755
        and snapshot.mode(formatter) == 0o755
    )

    literal_preservation = (
        text_a is not None
        and text_b is not None
        and value_a in text_a
        and value_b in text_b
        and "$literal *" in text_a
        and "$literal *" in text_b
    )

    return {
        "text_a": text_a,
        "text_b": text_b,
        "outputs_created": text_a is not None and text_b is not None,
        "first_dynamic_value": text_a == expected_a,
        "second_dynamic_value": text_b == expected_b,
        "literal_preservation": literal_preservation,
        "helpers_preserved": helpers_preserved,
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    variables = context["variables"]
    first = state(snapshots["after_first"], variables)
    second = state(snapshots["after_second"], variables)

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
        "Both first-run dynamic command invocations completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "outputs_created",
        first["outputs_created"],
        "Both requested dynamic report files were created.",
        "One or both requested dynamic report files were not created.",
    )

    book.check(
        "first_dynamic_value",
        first["first_dynamic_value"],
        "The first producer's output was formatted exactly.",
        "The first producer's dynamic value was not formatted correctly.",
    )

    book.check(
        "second_dynamic_value",
        first["second_dynamic_value"],
        "The second producer's output was formatted exactly.",
        "The second producer's dynamic value was not formatted correctly.",
    )

    book.check(
        "literal_preservation",
        first["literal_preservation"],
        "Spaces and shell metacharacters were preserved as literal data.",
        "Dynamic text containing spaces or shell metacharacters was changed or split.",
    )

    book.check(
        "helpers_preserved",
        first["helpers_preserved"],
        "All provided producer and formatter commands were preserved unchanged.",
        "One or more provided helper commands were modified or had permissions changed.",
    )

    idempotent = (
        first["first_dynamic_value"]
        and first["second_dynamic_value"]
        and second["first_dynamic_value"]
        and second["second_dynamic_value"]
        and first["helpers_preserved"]
        and second["helpers_preserved"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["text_a"] == second["text_a"]
        and first["text_b"] == second["text_b"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated execution preserves both correct dynamic reports.",
        "Repeated execution changed, appended to, or failed to preserve a dynamic report.",
    )

    return book.finalize()
