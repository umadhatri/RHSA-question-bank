#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grader.api import SnapshotSet  # noqa: E402
from grader.validation import (  # noqa: E402
    ValidationError,
    load_yaml,
    validate_grader_signature,
    validate_lab_config,
)

RUNNER_VERSION = "0.4.0"
RESULT_CONTRACT_VERSION = 1
LAB_SCHEMA = REPO_ROOT / "schemas" / "lab.schema.json"


class RunnerError(RuntimeError):
    pass


def run_cmd(
    args: list[str],
    *,
    timeout: int | float | None = None,
    check: bool = False,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            text=True,
            capture_output=capture,
            timeout=timeout,
            check=check,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(f"Command timed out after {timeout}s: {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        raise RunnerError(
            f"Command failed ({exc.returncode}): {' '.join(args)}\n"
            f"stdout:\n{exc.stdout or ''}\n"
            f"stderr:\n{exc.stderr or ''}"
        ) from exc


def require_docker() -> None:
    if shutil.which("docker") is None:
        raise RunnerError("Docker CLI was not found in PATH.")
    probe = run_cmd(["docker", "info"], timeout=10)
    if probe.returncode != 0:
        raise RunnerError(
            "Docker is installed but the daemon is not available.\n"
            + (probe.stderr or probe.stdout or "")
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_lab_package(lab_dir: Path) -> str:
    """Hash grading-relevant lab content, excluding instructor reference answers."""
    digest = hashlib.sha256()
    excluded_parts = {"reference", "__pycache__"}
    files = [
        p for p in lab_dir.rglob("*")
        if p.is_file()
        and not any(part in excluded_parts for part in p.relative_to(lab_dir).parts)
        and p.suffix != ".pyc"
    ]
    for path in sorted(files, key=lambda p: p.as_posix()):
        rel = path.relative_to(lab_dir).as_posix().encode()
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def image_exists(image: str) -> bool:
    return run_cmd(["docker", "image", "inspect", image]).returncode == 0


def image_id(image: str) -> str | None:
    cp = run_cmd(["docker", "image", "inspect", "--format", "{{.Id}}", image])
    return cp.stdout.strip() if cp.returncode == 0 else None


def ensure_image(
    lab: dict[str, Any],
    auto_build: bool,
    image_override: str | None = None,
) -> str:
    env = lab.get("environment", {})
    image = image_override or env.get("image")
    if not image:
        raise RunnerError("lab.yaml is missing environment.image and no --image-override was supplied")
    if image_exists(image):
        return image
    if not auto_build:
        raise RunnerError(
            f"Docker image {image!r} does not exist. Build it first or pass --build-image."
        )

    context_value = env.get("build_context")
    if not context_value:
        raise RunnerError(f"Image {image!r} is missing and no build_context is configured.")
    context = (REPO_ROOT / context_value).resolve()
    if not context.exists():
        raise RunnerError(f"Configured build context does not exist: {context}")

    print(f"[runner] Building missing image {image} ...")
    result = run_cmd(["docker", "build", "-t", image, str(context)], capture=False)
    if result.returncode != 0:
        raise RunnerError(f"Failed to build {image}")
    return image


def generate_variables(specs: dict[str, Any], seed: int) -> dict[str, str]:
    rng = random.Random(seed)
    variables: dict[str, str] = {}
    for name, spec in specs.items():
        kind = (spec or {}).get("type", "literal")
        if kind == "random_username":
            variables[name] = f"student_{rng.randrange(100000, 999999)}"
        elif kind == "random_group":
            variables[name] = f"team_{rng.randrange(100000, 999999)}"
        elif kind == "random_token":
            # Deliberately seed-derived so --seed fully reproduces a grading attempt.
            variables[name] = f"{rng.getrandbits(48):012x}"
        elif kind == "random_ipv4":
            # Documentation-only TEST-NET-3 range (RFC 5737); never a real public target.
            host_min = max(1, int((spec or {}).get("min", 1)))
            host_max = min(254, int((spec or {}).get("max", 254)))
            if host_min > host_max:
                raise RunnerError(f"random_ipv4 min cannot exceed max for {name}")
            variables[name] = f"203.0.113.{rng.randint(host_min, host_max)}"
        elif kind == "random_int":
            minimum = int((spec or {}).get("min", 1))
            maximum = int((spec or {}).get("max", 100))
            if minimum > maximum:
                raise RunnerError(f"random_int min cannot exceed max for {name}")
            variables[name] = str(rng.randint(minimum, maximum))
        elif kind == "literal":
            variables[name] = str((spec or {}).get("value", ""))
        else:
            raise RunnerError(f"Unsupported variable generator {kind!r} for {name}")
    return variables


_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render(value: str, variables: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise RunnerError(f"Unknown execution variable: {key}")
        return variables[key]

    return _VAR_PATTERN.sub(repl, value)


def docker_exec(container: str, command: list[str], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        cp = subprocess.run(
            ["docker", "exec", container, *command],
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        timed_out = False
        rc = cp.returncode
        stdout = cp.stdout
        stderr = cp.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        rc = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        run_cmd(["docker", "kill", container], timeout=10)

    return {
        "returncode": rc,
        "stdout": (stdout or "")[-16000:],
        "stderr": (stderr or "")[-16000:],
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def export_snapshot(container: str, destination: Path) -> None:
    exported = run_cmd(["docker", "export", "-o", str(destination), container], timeout=60)
    if exported.returncode != 0:
        raise RunnerError(f"Could not export grading snapshot:\n{exported.stderr}")


def load_grader(path: Path):
    spec = importlib.util.spec_from_file_location(f"lab_grader_{path.parent.name}", path)
    if spec is None or spec.loader is None:
        raise RunnerError(f"Could not load grader: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "grade"):
        raise RunnerError(f"{path} must define grade(lab, context, snapshots)")
    try:
        validate_grader_signature(module.grade)
    except ValidationError as exc:
        raise RunnerError(str(exc)) from exc
    return module.grade


def pretty_print(result: dict[str, Any]) -> None:
    print()
    print(f"Lab: {result['lab_id']} — {result['title']}")
    print("=" * 72)
    for item in result["tests"]:
        status = "PASS" if item["passed"] else "FAIL"
        print(
            f"[{status:4}] {item['id']:<26} "
            f"{item['points']:>3}/{item['max_points']:<3}  {item['feedback']}"
        )
    print("-" * 72)
    print(f"Final score: {result['score']}/{result['max_score']}")
    print(f"Pass mark:   {result['pass_score']}")
    print(f"Outcome:     {'PASS' if result['passed'] else 'FAIL'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Bash lab submission in Docker.")
    parser.add_argument("--lab", required=True, help="Path to the lab question directory")
    parser.add_argument("--submission", required=True, help="Path to the student's Bash script")
    parser.add_argument("--seed", type=int, help="Deterministic randomized-input seed")
    parser.add_argument("--json-out", help="Write structured grading result to this file")
    parser.add_argument(
        "--build-image",
        action="store_true",
        help="Build the configured Docker image automatically if it is missing",
    )
    parser.add_argument(
        "--image-override",
        help=(
            "Use this Docker image instead of environment.image from lab.yaml. "
            "Production workers use this to select an immutable/private ECR sandbox image."
        ),
    )
    args = parser.parse_args()

    lab_dir = Path(args.lab).resolve()
    submission = Path(args.submission).resolve()
    lab_yaml = lab_dir / "lab.yaml"
    setup_script = lab_dir / "setup.sh"
    grader_script = lab_dir / "grader.py"

    for required in (lab_yaml, setup_script, grader_script, submission):
        if not required.exists():
            raise RunnerError(f"Required file does not exist: {required}")

    lab = load_yaml(lab_yaml)
    try:
        validate_lab_config(lab, LAB_SCHEMA)
    except ValidationError as exc:
        raise RunnerError(str(exc)) from exc

    require_docker()
    image = ensure_image(lab, auto_build=args.build_image, image_override=args.image_override)

    seed = args.seed if args.seed is not None else secrets.randbelow(2**31 - 1)
    variables = generate_variables(lab.get("variables", {}), seed)

    configured_filename = lab.get("submission", {}).get("filename", "answer.sh")
    container_submission = f"/submission/{configured_filename}"

    exec_template = lab.get("execution", {}).get("command")
    if not isinstance(exec_template, list) or not exec_template:
        raise RunnerError("lab.yaml execution.command must be a non-empty list")
    command = [render(str(item), variables) for item in exec_template]

    env = lab.get("environment", {})
    timeout = int(env.get("timeout_seconds", 20))
    memory = str(env.get("memory", "512m"))
    cpus = str(env.get("cpus", "1.0"))
    pids = str(env.get("pids_limit", 128))

    container = f"rhsa-grade-{lab.get('id','lab').lower()}-{secrets.token_hex(4)}"
    tempdir = Path(tempfile.mkdtemp(prefix="rhsa-grade-"))
    first_snapshot_path = tempdir / "after-first.tar"
    second_snapshot_path = tempdir / "after-second.tar"

    context: dict[str, Any] = {
        "seed": seed,
        "variables": variables,
        "syntax_ok": False,
        "setup": {},
        "first_run": {},
        "second_run": {},
    }

    try:
        create = [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "--hostname",
            "rhsa-grader",
            "--network",
            "none",
            "--memory",
            memory,
            "--cpus",
            cpus,
            "--pids-limit",
            pids,
            "--security-opt",
            "no-new-privileges:true",
            image,
            "sleep",
            "infinity",
        ]
        created = run_cmd(create, timeout=60)
        if created.returncode != 0:
            raise RunnerError(f"Could not create grading container:\n{created.stderr}")

        # Trusted setup is present only during setup and removed before student code runs.
        run_cmd(["docker", "cp", str(setup_script), f"{container}:/tmp/lab-setup.sh"], check=True)
        # Setup receives generated values as environment variables. They are not
        # exported into the later student process unless the lab explicitly passes
        # them as command-line arguments via execution.command.
        setup_env = [f"{key}={value}" for key, value in variables.items()]
        setup_result = docker_exec(
            container,
            ["env", *setup_env, "bash", "/tmp/lab-setup.sh"],
            timeout=timeout,
        )
        context["setup"] = setup_result
        if setup_result["returncode"] != 0:
            raise RunnerError(
                "Lab setup failed.\n"
                f"stdout:\n{setup_result['stdout']}\n"
                f"stderr:\n{setup_result['stderr']}"
            )
        docker_exec(container, ["rm", "-f", "/tmp/lab-setup.sh"], timeout=5)

        run_cmd(["docker", "cp", str(submission), f"{container}:{container_submission}"], check=True)
        docker_exec(container, ["chmod", "0700", container_submission], timeout=5)

        syntax = docker_exec(container, ["bash", "-n", container_submission], timeout=5)
        context["syntax_ok"] = syntax["returncode"] == 0
        context["syntax"] = syntax

        if context["syntax_ok"]:
            context["first_run"] = docker_exec(container, command, timeout=timeout)
            export_snapshot(container, first_snapshot_path)

            if not context["first_run"].get("timed_out"):
                context["second_run"] = docker_exec(container, command, timeout=timeout)
                export_snapshot(container, second_snapshot_path)
            else:
                context["second_run"] = {
                    "returncode": 124,
                    "stdout": "",
                    "stderr": "Skipped because first run timed out.",
                    "timed_out": True,
                    "duration_seconds": 0,
                }
                shutil.copyfile(first_snapshot_path, second_snapshot_path)
        else:
            context["first_run"] = {
                "returncode": 2,
                "stdout": "",
                "stderr": "Submission was not executed because Bash syntax validation failed.",
                "timed_out": False,
                "duration_seconds": 0,
            }
            context["second_run"] = dict(context["first_run"])
            export_snapshot(container, first_snapshot_path)
            shutil.copyfile(first_snapshot_path, second_snapshot_path)

        # Stop before host-side grading. Any background processes spawned by the submission die here.
        run_cmd(["docker", "stop", "-t", "1", container], timeout=10)

        grade_fn = load_grader(grader_script)
        with SnapshotSet(
            {
                "after_first": str(first_snapshot_path),
                "after_second": str(second_snapshot_path),
            }
        ) as snapshots:
            grade_result = grade_fn(lab, context, snapshots)

        expected_max = int(lab["grading"]["total_points"])
        if grade_result["max_score"] != expected_max:
            raise RunnerError(
                f"Rubric totals {grade_result['max_score']} points but grading.total_points is {expected_max}."
            )

        pass_score = int(lab["grading"].get("pass_score", expected_max))
        result = {
            "contract_version": RESULT_CONTRACT_VERSION,
            "runner_version": RUNNER_VERSION,
            "lab_id": lab["id"],
            "title": lab["title"],
            "lab_version": lab.get("version", "1"),
            "score": grade_result["score"],
            "max_score": grade_result["max_score"],
            "pass_score": pass_score,
            "passed": grade_result["score"] >= pass_score,
            "tests": grade_result["tests"],
            "metadata": {
                "seed": seed,
                "variables": variables,
                "image": image,
                "image_id": image_id(image),
                "submission_filename": submission.name,
                "submission_sha256": sha256_file(submission),
                "lab_package_sha256": hash_lab_package(lab_dir),
                "first_run": context["first_run"],
                "second_run": context["second_run"],
            },
        }

        pretty_print(result)
        if args.json_out:
            out_path = Path(args.json_out)
            out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"\nStructured result written to {out_path}")

        return 0 if result["passed"] else 2

    finally:
        run_cmd(["docker", "rm", "-f", container], timeout=15)
        shutil.rmtree(tempdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RunnerError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
