from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def stdout_text(token: str, code: int, prefix: str) -> str:
    return f"OUT {prefix}-{token} code-{code} [ok] $literal *\n"


def stderr_text(token: str, code: int, prefix: str) -> str:
    return f"ERR {prefix}-{token} code-{code} [warn] $literal *\n"


def emitter_text(token: str, code: int, prefix: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' 'OUT {prefix}-{token} code-{code} [ok] $literal *'\n"
        f"printf '%s\\n' 'ERR {prefix}-{token} code-{code} [warn] $literal *' >&2\n"
    )


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    code_a = int(variables["CODE_A"])
    code_b = int(variables["CODE_B"])

    stdout_a_path = f"/workspace/stdout_a_{token}.txt"
    stderr_a_path = f"/workspace/stderr_a_{token}.txt"
    stdout_b_path = f"/workspace/stdout_b_{token}.txt"
    stderr_b_path = f"/workspace/stderr_b_{token}.txt"
    emitter_a_path = f"/workspace/emitter_a_{token}"
    emitter_b_path = f"/workspace/emitter_b_{token}"

    stdout_a = snapshot.read_text(stdout_a_path)
    stderr_a = snapshot.read_text(stderr_a_path)
    stdout_b = snapshot.read_text(stdout_b_path)
    stderr_b = snapshot.read_text(stderr_b_path)

    expected_stdout_a = stdout_text(token, code_a, "alpha")
    expected_stderr_a = stderr_text(token, code_a, "alpha")
    expected_stdout_b = stdout_text(token, code_b, "beta")
    expected_stderr_b = stderr_text(token, code_b, "beta")

    outputs_created = all(
        value is not None
        for value in (stdout_a, stderr_a, stdout_b, stderr_b)
    )

    stdout_routing = (
        stdout_a == expected_stdout_a
        and stdout_b == expected_stdout_b
    )

    stderr_routing = (
        stderr_a == expected_stderr_a
        and stderr_b == expected_stderr_b
    )

    streams_separated = (
        stdout_routing
        and stderr_routing
        and expected_stderr_a not in (stdout_a or "")
        and expected_stderr_b not in (stdout_b or "")
        and expected_stdout_a not in (stderr_a or "")
        and expected_stdout_b not in (stderr_b or "")
    )

    helpers_preserved = (
        snapshot.read_text(emitter_a_path)
        == emitter_text(token, code_a, "alpha")
        and snapshot.read_text(emitter_b_path)
        == emitter_text(token, code_b, "beta")
        and snapshot.mode(emitter_a_path) == 0o755
        and snapshot.mode(emitter_b_path) == 0o755
    )

    return {
        "stdout_a": stdout_a,
        "stderr_a": stderr_a,
        "stdout_b": stdout_b,
        "stderr_b": stderr_b,
        "outputs_created": outputs_created,
        "stdout_routing": stdout_routing,
        "stderr_routing": stderr_routing,
        "streams_separated": streams_separated,
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
        "Both first-run emitter invocations completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "outputs_created",
        first["outputs_created"],
        "All requested output files were created.",
        "One or more requested output files were not created.",
    )

    book.check(
        "stdout_routing",
        first["stdout_routing"],
        "Standard output from both emitters was routed exactly.",
        "Standard output was missing, altered, swapped, or routed incorrectly.",
    )

    book.check(
        "stderr_routing",
        first["stderr_routing"],
        "Standard error from both emitters was routed exactly.",
        "Standard error was missing, altered, swapped, or routed incorrectly.",
    )

    book.check(
        "streams_separated",
        first["streams_separated"],
        "Standard output and standard error remained strictly separated.",
        "The output streams were merged, crossed, or contaminated.",
    )

    book.check(
        "helpers_preserved",
        first["helpers_preserved"],
        "Both provided emitter commands were preserved unchanged.",
        "A provided emitter command was modified or had permissions changed.",
    )

    idempotent = (
        first["stdout_routing"]
        and first["stderr_routing"]
        and first["streams_separated"]
        and second["stdout_routing"]
        and second["stderr_routing"]
        and second["streams_separated"]
        and first["helpers_preserved"]
        and second["helpers_preserved"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["stdout_a"] == second["stdout_a"]
        and first["stderr_a"] == second["stderr_a"]
        and first["stdout_b"] == second["stdout_b"]
        and first["stderr_b"] == second["stderr_b"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated execution preserves all four correct routed files.",
        "Repeated execution changed, appended to, or failed to preserve routed output.",
    )

    return book.finalize()
