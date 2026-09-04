from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def tool_text(token: str, value: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' '{value}-{token}'\n"
    )


def probe_text() -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "\n"
        "resolved_tool=$(command -v range-tool 2>/dev/null || true)\n"
        "tool_value=$(range-tool 2>/dev/null || true)\n"
        "resolved_legacy=$(command -v legacy-helper 2>/dev/null || true)\n"
        "legacy_value=$(legacy-helper 2>/dev/null || true)\n"
        "\n"
        "printf 'SESSION=%s\\n' \"${TUPE_SESSION-<unset>}\"\n"
        "printf 'RESOLVED_TOOL=%s\\n' \"$resolved_tool\"\n"
        "printf 'TOOL_VALUE=%s\\n' \"$tool_value\"\n"
        "printf 'RESOLVED_LEGACY=%s\\n' \"$resolved_legacy\"\n"
        "printf 'LEGACY_VALUE=%s\\n' \"$legacy_value\"\n"
        "printf 'PATH=%s\\n' \"$PATH\"\n"
    )


def expected_report(
    *,
    session: str,
    tool_path: str,
    tool_value: str,
    legacy_path: str,
    path_value: str,
) -> str:
    return (
        f"SESSION={session}\n"
        f"RESOLVED_TOOL={tool_path}\n"
        f"TOOL_VALUE={tool_value}\n"
        f"RESOLVED_LEGACY={legacy_path}\n"
        f"LEGACY_VALUE=legacy-{session.rsplit(' ', 1)[-1]}\n"
        f"PATH={path_value}\n"
    )


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])

    output_a = f"/workspace/environment_a_{token}.txt"
    output_b = f"/workspace/environment_b_{token}.txt"

    tool_a_dir = f"/workspace/tool_a_{token}"
    tool_b_dir = f"/workspace/tool_b_{token}"
    decoy_dir = f"/workspace/decoy_bin_{token}"
    legacy_dir = f"/workspace/legacy_bin_{token}"

    tool_a = f"{tool_a_dir}/range-tool"
    tool_b = f"{tool_b_dir}/range-tool"
    decoy = f"{decoy_dir}/range-tool"
    legacy = f"{legacy_dir}/legacy-helper"
    probe = f"/workspace/environment_probe_{token}"

    session_a = f"alpha session {token}"
    session_b = f"beta session {token}"

    base_path = f"{decoy_dir}:{legacy_dir}:/usr/local/bin:/usr/bin:/bin"
    path_a = f"{tool_a_dir}:{base_path}"
    path_b = f"{tool_b_dir}:{base_path}"

    expected_a = expected_report(
        session=session_a,
        tool_path=tool_a,
        tool_value=f"alpha-{token}",
        legacy_path=legacy,
        path_value=path_a,
    )
    expected_b = expected_report(
        session=session_b,
        tool_path=tool_b,
        tool_value=f"beta-{token}",
        legacy_path=legacy,
        path_value=path_b,
    )

    text_a = snapshot.read_text(output_a)
    text_b = snapshot.read_text(output_b)

    session_export = (
        text_a is not None
        and text_b is not None
        and f"SESSION={session_a}\n" in text_a
        and f"SESSION={session_b}\n" in text_b
    )

    path_precedence = (
        text_a is not None
        and text_b is not None
        and f"RESOLVED_TOOL={tool_a}\n" in text_a
        and f"TOOL_VALUE=alpha-{token}\n" in text_a
        and f"RESOLVED_TOOL={tool_b}\n" in text_b
        and f"TOOL_VALUE=beta-{token}\n" in text_b
    )

    path_preservation = (
        text_a is not None
        and text_b is not None
        and f"RESOLVED_LEGACY={legacy}\n" in text_a
        and f"LEGACY_VALUE=legacy-{token}\n" in text_a
        and f"PATH={path_a}\n" in text_a
        and f"RESOLVED_LEGACY={legacy}\n" in text_b
        and f"LEGACY_VALUE=legacy-{token}\n" in text_b
        and f"PATH={path_b}\n" in text_b
    )

    helpers_preserved = (
        snapshot.read_text(tool_a) == tool_text(token, "alpha")
        and snapshot.read_text(tool_b) == tool_text(token, "beta")
        and snapshot.read_text(decoy) == tool_text(token, "decoy")
        and snapshot.read_text(legacy) == tool_text(token, "legacy")
        and snapshot.read_text(probe) == probe_text()
        and snapshot.mode(tool_a) == 0o755
        and snapshot.mode(tool_b) == 0o755
        and snapshot.mode(decoy) == 0o755
        and snapshot.mode(legacy) == 0o755
        and snapshot.mode(probe) == 0o755
    )

    return {
        "text_a": text_a,
        "text_b": text_b,
        "outputs_created": text_a is not None and text_b is not None,
        "session_export": session_export,
        "path_precedence": path_precedence,
        "path_preservation": path_preservation,
        "exact_reports": text_a == expected_a and text_b == expected_b,
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
        "Both first-run environment invocations completed successfully.",
        f"The first execution returned exit code {first_rc}.",
    )

    book.check(
        "outputs_created",
        first["outputs_created"],
        "Both requested environment reports were created.",
        "One or both requested environment reports were not created.",
    )

    book.check(
        "session_export",
        first["session_export"],
        "Both session values were visible in the child process.",
        "TUPE_SESSION was missing, changed, or not inherited by a child process.",
    )

    book.check(
        "path_precedence",
        first["path_precedence"],
        "The requested tool directory takes precedence over the decoy directory.",
        "PATH did not resolve range-tool from the requested leading directory.",
    )

    book.check(
        "path_preservation",
        first["path_preservation"],
        "The original PATH was preserved after the new leading tool directory.",
        "The inherited PATH was replaced, reordered, or otherwise not preserved.",
    )

    book.check(
        "exact_reports",
        first["exact_reports"],
        "Both child environment reports exactly match the required state.",
        "One or both child environment reports contain unexpected state.",
    )

    book.check(
        "helpers_preserved",
        first["helpers_preserved"],
        "All supplied commands and probe files were preserved unchanged.",
        "A supplied command, probe, or executable mode was modified.",
    )

    idempotent = (
        first["exact_reports"]
        and second["exact_reports"]
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
        "Repeated execution preserves both correct environment reports.",
        "Repeated execution changed, appended to, or failed to preserve a report.",
    )

    return book.finalize()
