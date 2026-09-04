from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def project_value(token: str, build: int, prefix: str) -> str:
    return f"{prefix}-{token} build-{build} [release] *"


def owner_value(token: str, label: str) -> str:
    return f"Owner {label} {token} $ops"


def expected_document(project: str, owner: str) -> str:
    return (
        "BEGIN NOTICE\n"
        f"project={project}\n"
        f"owner={owner}\n"
        "home-literal=$HOME\n"
        "command-literal=$(date)\n"
        "backtick-literal=`whoami`\n"
        "END NOTICE\n"
    )


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    build_a = int(variables["BUILD_A"])
    build_b = int(variables["BUILD_B"])

    output_a = f"/workspace/notice_a_{token}.txt"
    output_b = f"/workspace/notice_b_{token}.txt"

    project_a = project_value(token, build_a, "alpha")
    project_b = project_value(token, build_b, "beta")
    owner_a = owner_value(token, "A")
    owner_b = owner_value(token, "B")

    expected_a = expected_document(project_a, owner_a)
    expected_b = expected_document(project_b, owner_b)

    text_a = snapshot.read_text(output_a)
    text_b = snapshot.read_text(output_b)

    outputs_created = text_a is not None and text_b is not None

    first_document = text_a == expected_a
    second_document = text_b == expected_b

    dynamic_fields = (
        text_a is not None
        and text_b is not None
        and f"project={project_a}\n" in text_a
        and f"owner={owner_a}\n" in text_a
        and f"project={project_b}\n" in text_b
        and f"owner={owner_b}\n" in text_b
    )

    literals = (
        "home-literal=$HOME\n",
        "command-literal=$(date)\n",
        "backtick-literal=`whoami`\n",
    )
    literal_shell_text = (
        text_a is not None
        and text_b is not None
        and all(item in text_a for item in literals)
        and all(item in text_b for item in literals)
    )

    return {
        "text_a": text_a,
        "text_b": text_b,
        "outputs_created": outputs_created,
        "first_document": first_document,
        "second_document": second_document,
        "dynamic_fields": dynamic_fields,
        "literal_shell_text": literal_shell_text,
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
        "Both first-run notice generations completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "outputs_created",
        first["outputs_created"],
        "Both requested notice files were created.",
        "One or both requested notice files were not created.",
    )

    book.check(
        "first_document",
        first["first_document"],
        "The first generated notice matches the required document exactly.",
        "The first generated notice is missing, reordered, expanded, or otherwise incorrect.",
    )

    book.check(
        "second_document",
        first["second_document"],
        "The second generated notice matches the required document exactly.",
        "The second generated notice is missing, hard-coded, expanded, or otherwise incorrect.",
    )

    book.check(
        "dynamic_fields",
        first["dynamic_fields"],
        "Both PROJECT and OWNER arguments were substituted exactly in both notices.",
        "One or more dynamic PROJECT/OWNER values were missing, changed, or hard-coded.",
    )

    book.check(
        "literal_shell_text",
        first["literal_shell_text"],
        "Shell-looking text remained literal instead of being expanded or executed.",
        "One or more literal shell expressions were expanded, executed, or altered.",
    )

    idempotent = (
        first["first_document"]
        and first["second_document"]
        and second["first_document"]
        and second["second_document"]
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
        "Repeated execution preserves both exact notice files.",
        "Repeated execution changed, appended to, or failed to preserve a notice.",
    )

    return book.finalize()
