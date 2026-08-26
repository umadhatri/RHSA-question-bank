#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

WORKER_VERSION = "0.1.0"
DEFAULT_ROOT = Path(os.environ.get("QUESTION_BANK_ROOT", "/opt/question-bank"))


class WorkerError(RuntimeError):
    pass


def load_lab_id(lab_yaml: Path) -> str | None:
    try:
        payload = yaml.safe_load(lab_yaml.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    lab_id = payload.get("id")
    return str(lab_id) if lab_id else None


def resolve_lab(root: Path, lab_id: str) -> Path:
    """Resolve exactly one lab directory by its declared lab.yaml id."""
    labs_root = root / "labs"
    matches: list[Path] = []
    if labs_root.is_dir():
        for lab_yaml in sorted(labs_root.glob("*/*/lab.yaml")):
            if load_lab_id(lab_yaml) == lab_id:
                matches.append(lab_yaml.parent)

    if not matches:
        raise WorkerError(f"Unknown lab id: {lab_id}")
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise WorkerError(f"Duplicate lab id {lab_id}: {rendered}")
    return matches[0]


def tail(value: str | None, limit: int = 16000) -> str:
    return (value or "")[-limit:]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Trusted CyberRange grading worker. Runs the private question-bank runner "
            "against an externally supplied Bash submission."
        )
    )
    parser.add_argument("--lab-id", required=True)
    parser.add_argument("--submission", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--question-bank-root",
        default=str(DEFAULT_ROOT),
        help="Question-bank root baked into the worker image.",
    )
    args = parser.parse_args()

    root = Path(args.question_bank_root).resolve()
    runner = root / "grader" / "runner.py"
    submission = Path(args.submission).resolve()
    result_path = Path(args.result).resolve()

    if not runner.is_file():
        raise WorkerError(f"Question-bank runner not found: {runner}")
    if not submission.is_file():
        raise WorkerError(f"Submission not found: {submission}")

    lab_dir = resolve_lab(root, args.lab_id)

    # The question-bank runner writes its full internal result to a worker-private
    # temporary file. We only publish it to --result after a completed grading run.
    with tempfile.TemporaryDirectory(prefix="rhsa-worker-") as tmp:
        internal_result = Path(tmp) / "result.json"
        command = [
            sys.executable,
            str(runner),
            "--lab",
            str(lab_dir),
            "--submission",
            str(submission),
            "--json-out",
            str(internal_result),
        ]
        if args.seed is not None:
            command.extend(["--seed", str(args.seed)])

        completed = subprocess.run(command, text=True, capture_output=True)

        # Preserve the useful terminal transcript in worker logs. The runner's
        # pretty output contains rubric feedback, not hidden generated variables.
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)

        # runner.py uses 0 for academic PASS and 2 for academic FAIL. Both mean the
        # grading infrastructure worked and must therefore be a successful worker job.
        if completed.returncode in (0, 2) and internal_result.is_file():
            payload = json.loads(internal_result.read_text(encoding="utf-8"))
            metadata = payload.setdefault("metadata", {})
            metadata["worker"] = {
                "version": WORKER_VERSION,
                "question_bank_revision": os.environ.get(
                    "QUESTION_BANK_REVISION", "unknown"
                ),
            }
            write_json(result_path, payload)
            print(
                f"[worker] Grading completed for {args.lab_id}: "
                f"{payload.get('score')}/{payload.get('max_score')} "
                f"({'PASS' if payload.get('passed') else 'FAIL'})"
            )
            return 0

        error_payload = {
            "status": "ERROR",
            "worker_version": WORKER_VERSION,
            "lab_id": args.lab_id,
            "runner_returncode": completed.returncode,
            "error": "Question-bank runner failed before producing a grading result.",
            "runner_stdout": tail(completed.stdout),
            "runner_stderr": tail(completed.stderr),
        }
        write_json(result_path, error_payload)
        print(
            f"[worker] Infrastructure failure while grading {args.lab_id}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
