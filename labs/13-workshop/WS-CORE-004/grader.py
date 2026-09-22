from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def setup_value(context: dict[str, Any], key: str) -> int | None:
    stdout = str(context.get("setup", {}).get("stdout", ""))
    prefix = f"{key}="

    for line in stdout.splitlines():
        if line.startswith(prefix):
            try:
                return int(line[len(prefix):].strip())
            except ValueError:
                return None

    return None


def process_state(
    snapshot: RootfsSnapshot,
    path: str,
) -> list[dict[str, int | str]]:
    text = snapshot.read_text(path) or ""
    result: list[dict[str, int | str]] = []

    for raw_line in text.splitlines():
        fields = raw_line.split()

        if len(fields) != 3:
            continue

        try:
            pid = int(fields[0])
            nice = int(fields[2])
        except ValueError:
            continue

        result.append(
            {
                "pid": pid,
                "state": fields[1],
                "nice": nice,
            }
        )

    return result


def active_processes(
    processes: list[dict[str, int | str]],
) -> list[dict[str, int | str]]:
    return [
        proc
        for proc in processes
        if proc["state"] != "Z"
    ]


def inspect_state(
    snapshot: RootfsSnapshot,
    runaway_pid: int | None,
    worker_pid: int | None,
    control_pid: int | None,
) -> dict[str, bool]:
    runaway = active_processes(
        process_state(
            snapshot,
            "/run/cyberrange-runaway-state",
        )
    )

    worker = active_processes(
        process_state(
            snapshot,
            "/run/cyberrange-worker-state",
        )
    )

    control = active_processes(
        process_state(
            snapshot,
            "/run/cyberrange-control-state",
        )
    )

    original_worker = [
        proc
        for proc in worker
        if proc["pid"] == worker_pid
    ]

    original_control = [
        proc
        for proc in control
        if proc["pid"] == control_pid
    ]

    original_runaway_alive = any(
        proc["pid"] == runaway_pid
        for proc in runaway
    )

    worker_preserved = (
        worker_pid is not None
        and len(original_worker) == 1
    )

    control_preserved = (
        control_pid is not None
        and len(original_control) == 1
    )

    worker_priority = (
        worker_preserved
        and original_worker[0]["nice"] == 10
    )

    control_priority = (
        control_preserved
        and original_control[0]["nice"] == 0
    )

    no_extra_processes = (
        len(runaway) == 0
        and len(worker) == 1
        and len(control) == 1
    )

    return {
        "runaway_terminated": (
            runaway_pid is not None
            and not original_runaway_alive
            and len(runaway) == 0
        ),
        "worker_preserved": worker_preserved,
        "worker_priority": worker_priority,
        "control_preserved": control_preserved,
        "control_priority": control_priority,
        "no_extra_processes": no_extra_processes,
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    runaway_pid = setup_value(
        context,
        "RUNAWAY_PID",
    )

    worker_pid = setup_value(
        context,
        "WORKER_PID",
    )

    control_pid = setup_value(
        context,
        "CONTROL_PID",
    )

    first_snapshot = snapshots["after_first"]
    second_snapshot = snapshots["after_second"]

    first = inspect_state(
        first_snapshot,
        runaway_pid,
        worker_pid,
        control_pid,
    )

    second = inspect_state(
        second_snapshot,
        runaway_pid,
        worker_pid,
        control_pid,
    )

    book.check(
        "syntax",
        context.get("syntax_ok", False),
        "Bash syntax is valid.",
        "Bash syntax validation failed.",
    )

    first_rc = int(
        context.get("first_run", {}).get("returncode", 1)
    )

    first_timeout = bool(
        context.get("first_run", {}).get("timed_out", False)
    )

    book.check(
        "first_run_exit",
        first_rc == 0 and not first_timeout,
        "The first execution exited successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "runaway_terminated",
        first["runaway_terminated"],
        "The original runaway process was terminated.",
        "The original runaway process is still active or was replaced.",
    )

    book.check(
        "worker_preserved",
        first["worker_preserved"],
        "The original worker process remains running.",
        "The original worker process was terminated or replaced.",
    )

    book.check(
        "worker_priority",
        first["worker_priority"],
        "The existing worker process has nice value 10.",
        "The existing worker process does not have nice value 10.",
    )

    book.check(
        "control_preserved",
        first["control_preserved"],
        "The original control process remains running.",
        "The original control process was terminated or replaced.",
    )

    book.check(
        "control_priority",
        first["control_priority"],
        "The control process retains nice value 0.",
        "The control process priority was modified.",
    )

    book.check(
        "no_extra_processes",
        first["no_extra_processes"],
        "No additional managed processes were created.",
        (
            "Unexpected active cr_runaway, cr_worker, or "
            "cr_control processes were detected."
        ),
    )

    second_rc = int(
        context.get("second_run", {}).get("returncode", 1)
    )

    second_timeout = bool(
        context.get("second_run", {}).get("timed_out", False)
    )

    required_state = (
        "runaway_terminated",
        "worker_preserved",
        "worker_priority",
        "control_preserved",
        "control_priority",
        "no_extra_processes",
    )

    first_complete = all(
        first[key]
        for key in required_state
    )

    second_complete = all(
        second[key]
        for key in required_state
    )

    idempotent = (
        first_rc == 0
        and second_rc == 0
        and not first_timeout
        and not second_timeout
        and first_complete
        and second_complete
    )

    book.check(
        "idempotency",
        idempotent,
        (
            "Repeated execution succeeds and preserves the "
            "complete required process state."
        ),
        (
            "The repeat execution did not preserve the "
            "complete required process state."
        ),
    )

    return book.finalize()
