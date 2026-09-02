from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def expected_input(token: str, prefix: str, count: int) -> str:
    return "".join(
        f"{prefix}-{token}-{index:02d}\n"
        for index in range(1, count + 1)
    )


def parse_probe(text: str | None) -> dict[str, int] | None:
    if text is None:
        return None

    result: dict[str, int] = {}

    for raw_line in text.splitlines():
        if "=" not in raw_line:
            continue

        key, value = raw_line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key not in {"A", "B"}:
            continue

        try:
            result[key] = int(value)
        except ValueError:
            return None

    return result if set(result) == {"A", "B"} else None


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    count_a = int(variables["COUNT_A"])
    count_b = int(variables["COUNT_B"])

    bin_dir = f"/workspace/student_bin_{token}"
    command = f"{bin_dir}/recordcount"
    input_a = f"/workspace/data_a_{token}.txt"
    input_b = f"/workspace/data_b_{token}.txt"
    probe = f"/workspace/command_probe_{token}.txt"
    resolved = f"/workspace/resolved_command_{token}.txt"

    command_exists = snapshot.is_file(command)
    mode = snapshot.mode(command)
    command_executable = bool(
        command_exists
        and mode is not None
        and (mode & 0o111)
    )

    resolved_text = (snapshot.read_text(resolved) or "").strip()
    path_resolution = resolved_text == command

    probe_values = parse_probe(snapshot.read_text(probe))
    argument_behavior = probe_values == {
        "A": count_a,
        "B": count_b,
    }

    input_preserved = (
        snapshot.read_text(input_a)
        == expected_input(token, "alpha", count_a)
        and snapshot.read_text(input_b)
        == expected_input(token, "beta", count_b)
    )

    return {
        "command_exists": command_exists,
        "command_executable": command_executable,
        "path_resolution": path_resolution,
        "argument_behavior": argument_behavior,
        "input_preserved": input_preserved,
        "command_bytes": snapshot.read_bytes(command),
        "command_mode": mode,
        "resolved_text": resolved_text,
        "probe_text": snapshot.read_text(probe),
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
        "The first installation and command probe completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "command_created",
        first["command_exists"],
        "recordcount was created in the requested bin directory.",
        "recordcount was not created at the required path.",
    )

    book.check(
        "command_executable",
        first["command_executable"],
        "The installed recordcount command is executable.",
        "The installed recordcount file is missing executable permission.",
    )

    book.check(
        "path_resolution",
        first["path_resolution"],
        "PATH resolves recordcount to the command installed in the requested bin directory.",
        "recordcount did not resolve through PATH to the student's installed command.",
    )

    book.check(
        "argument_behavior",
        first["argument_behavior"],
        "recordcount correctly processed multiple file arguments with randomized line counts.",
        "recordcount returned an incorrect result for one or more input files.",
    )

    book.check(
        "input_preserved",
        first["input_preserved"],
        "The source data files were preserved unchanged.",
        "One or more source data files were modified.",
    )

    idempotent = (
        first["command_exists"]
        and second["command_exists"]
        and first["command_executable"]
        and second["command_executable"]
        and first["path_resolution"]
        and second["path_resolution"]
        and first["argument_behavior"]
        and second["argument_behavior"]
        and first["input_preserved"]
        and second["input_preserved"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["command_bytes"] == second["command_bytes"]
        and first["command_mode"] == second["command_mode"]
        and first["resolved_text"] == second["resolved_text"]
        and first["probe_text"] == second["probe_text"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated installation preserves the same working command and behavior.",
        "Repeated installation changed, broke, or failed to preserve the installed command.",
    )

    return book.finalize()
