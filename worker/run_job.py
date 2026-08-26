#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

WORKER_VERSION = "0.2.0"
DEFAULT_ROOT = Path(os.environ.get("QUESTION_BANK_ROOT", "/opt/question-bank"))
DEFAULT_MAX_SUBMISSION_BYTES = 64 * 1024
DEFAULT_HTTP_TIMEOUT_SECONDS = 30


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def parse_optional_int(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def validate_http_url(value: str, *, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise WorkerError(f"{label} must be an absolute HTTP(S) URL.")
    return value


def download_submission(
    url: str,
    destination: Path,
    *,
    max_bytes: int = DEFAULT_MAX_SUBMISSION_BYTES,
    timeout_seconds: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> None:
    """Download a submission without ever logging the signed URL."""
    validate_http_url(url, label="Submission URL")
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": f"CyberRange-RHSA-Worker/{WORKER_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            declared = response.headers.get("Content-Length")
            if declared:
                try:
                    if int(declared) > max_bytes:
                        raise WorkerError(
                            f"Submission exceeds the {max_bytes}-byte worker limit."
                        )
                except ValueError:
                    pass
            data = response.read(max_bytes + 1)
    except WorkerError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WorkerError(f"Unable to download submission: {exc}") from exc

    if len(data) > max_bytes:
        raise WorkerError(f"Submission exceeds the {max_bytes}-byte worker limit.")
    if not data:
        raise WorkerError("Downloaded submission is empty.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    destination.chmod(0o600)


def upload_result(
    url: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> None:
    """PUT one JSON result to a short-lived signed HTTP(S) destination."""
    validate_http_url(url, label="Result URL")
    data = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
            "User-Agent": f"CyberRange-RHSA-Worker/{WORKER_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise WorkerError(f"Result upload returned HTTP {status}.")
    except WorkerError:
        raise
    except urllib.error.HTTPError as exc:
        raise WorkerError(f"Result upload returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WorkerError(f"Unable to upload grading result: {exc}") from exc


def publish_result(
    payload: dict[str, Any],
    *,
    result_path: Path | None,
    result_url: str | None,
    timeout_seconds: int,
) -> None:
    if result_path is not None:
        write_json(result_path, payload)
    else:
        assert result_url is not None
        upload_result(result_url, payload, timeout_seconds=timeout_seconds)


def docker_run(
    args: list[str],
    *,
    input_text: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorkerError(f"Command timed out after {timeout}s: {args[0]}") from exc
    except OSError as exc:
        raise WorkerError(f"Unable to execute {args[0]}: {exc}") from exc


def docker_image_exists(image: str) -> bool:
    return docker_run(["docker", "image", "inspect", image], timeout=20).returncode == 0


def docker_repo_digest(image: str) -> str | None:
    completed = docker_run(
        ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image],
        timeout=20,
    )
    if completed.returncode != 0:
        return None
    try:
        values = json.loads(completed.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return None
    return str(values[0]) if values else None


def ecr_registry_region(image: str) -> tuple[str, str] | None:
    registry = image.split("/", 1)[0]
    parts = registry.split(".")
    # 123456789012.dkr.ecr.ap-south-1.amazonaws.com/repository:tag
    if (
        len(parts) >= 6
        and parts[0].isdigit()
        and parts[1:3] == ["dkr", "ecr"]
        and parts[4] == "amazonaws"
        and parts[5] in {"com", "com.cn"}
    ):
        return registry, parts[3]
    # China domains split as ...amazonaws.com.cn, so handle them explicitly.
    if (
        len(parts) >= 7
        and parts[0].isdigit()
        and parts[1:3] == ["dkr", "ecr"]
        and parts[4:7] == ["amazonaws", "com", "cn"]
    ):
        return registry, parts[3]
    return None


def ecr_login(image: str) -> str | None:
    match = ecr_registry_region(image)
    if match is None:
        return None
    registry, region = match

    if shutil.which("aws") is None:
        raise WorkerError(
            "AWS CLI is required to authenticate Docker to a private ECR sandbox image."
        )

    token = docker_run(
        ["aws", "ecr", "get-login-password", "--region", region], timeout=30
    )
    if token.returncode != 0 or not token.stdout.strip():
        raise WorkerError(
            "Unable to obtain an ECR authorization token. "
            + tail(token.stderr or token.stdout, 2000)
        )

    login = docker_run(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        input_text=token.stdout,
        timeout=30,
    )
    if login.returncode != 0:
        raise WorkerError("Docker login to the ECR registry failed. " + tail(login.stderr, 2000))
    return registry


def prepare_base_image(image: str, *, pull: bool) -> dict[str, Any]:
    """Make an override sandbox image available to the host Docker daemon."""
    registry: str | None = None
    try:
        if pull:
            registry = ecr_login(image)
            pulled = docker_run(["docker", "pull", image], timeout=300)
            if pulled.returncode != 0:
                raise WorkerError("Unable to pull sandbox image. " + tail(pulled.stderr, 3000))
        elif not docker_image_exists(image):
            raise WorkerError(
                f"Sandbox image {image!r} is not present. Enable RHSA_PULL_BASE_IMAGE "
                "or pre-pull the image on the grading host."
            )

        return {
            "requested": image,
            "repo_digest": docker_repo_digest(image),
            "pulled": pull,
        }
    finally:
        if registry:
            # The worker is ephemeral, but explicitly discard the temporary ECR token.
            docker_run(["docker", "logout", registry], timeout=20)


def error_payload(lab_id: str | None, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ERROR",
        "worker_version": WORKER_VERSION,
        "lab_id": lab_id,
        "error": message,
    }
    payload.update(extra)
    return payload


def validate_io_args(args: argparse.Namespace) -> None:
    if not args.lab_id:
        raise WorkerError("A lab id is required (--lab-id or RHSA_LAB_ID).")
    if bool(args.submission) == bool(args.submission_url):
        raise WorkerError(
            "Specify exactly one submission source: --submission or --submission-url."
        )
    if bool(args.result) == bool(args.result_url):
        raise WorkerError("Specify exactly one result target: --result or --result-url.")
    if args.max_submission_bytes <= 0:
        raise WorkerError("max submission bytes must be positive.")
    if args.http_timeout_seconds <= 0:
        raise WorkerError("HTTP timeout must be positive.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Trusted CyberRange grading worker. Supports local paths for development "
            "and short-lived HTTP(S) object URLs for ECS grading jobs."
        )
    )
    parser.add_argument("--lab-id", default=os.environ.get("RHSA_LAB_ID"))
    parser.add_argument("--submission", default=os.environ.get("RHSA_SUBMISSION_PATH"))
    parser.add_argument("--submission-url", default=os.environ.get("RHSA_SUBMISSION_URL"))
    parser.add_argument("--result", default=os.environ.get("RHSA_RESULT_PATH"))
    parser.add_argument("--result-url", default=os.environ.get("RHSA_RESULT_URL"))
    parser.add_argument(
        "--seed",
        type=int,
        default=parse_optional_int(os.environ.get("RHSA_SEED")),
    )
    parser.add_argument(
        "--base-image",
        default=os.environ.get("RHSA_BASE_IMAGE"),
        help="Optional sandbox image override, normally an immutable/private ECR URI.",
    )
    parser.add_argument(
        "--pull-base-image",
        action="store_true",
        default=parse_bool(os.environ.get("RHSA_PULL_BASE_IMAGE")),
        help="Pull --base-image before grading. Private ECR images are authenticated via AWS CLI.",
    )
    parser.add_argument(
        "--max-submission-bytes",
        type=int,
        default=int(
            os.environ.get("RHSA_MAX_SUBMISSION_BYTES", DEFAULT_MAX_SUBMISSION_BYTES)
        ),
    )
    parser.add_argument(
        "--http-timeout-seconds",
        type=int,
        default=int(
            os.environ.get("RHSA_HTTP_TIMEOUT_SECONDS", DEFAULT_HTTP_TIMEOUT_SECONDS)
        ),
    )
    parser.add_argument(
        "--question-bank-root",
        default=str(DEFAULT_ROOT),
        help="Question-bank root baked into the worker image.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result_path = Path(args.result).resolve() if args.result else None
    result_url = args.result_url

    try:
        validate_io_args(args)
        root = Path(args.question_bank_root).resolve()
        runner = root / "grader" / "runner.py"
        if not runner.is_file():
            raise WorkerError(f"Question-bank runner not found: {runner}")

        lab_dir = resolve_lab(root, args.lab_id)

        with tempfile.TemporaryDirectory(prefix="rhsa-worker-job-") as tmp:
            tmpdir = Path(tmp)
            if args.submission:
                submission = Path(args.submission).resolve()
                if not submission.is_file():
                    raise WorkerError(f"Submission not found: {submission}")
            else:
                submission = tmpdir / "submission.sh"
                download_submission(
                    args.submission_url,
                    submission,
                    max_bytes=args.max_submission_bytes,
                    timeout_seconds=args.http_timeout_seconds,
                )

            sandbox_info: dict[str, Any] | None = None
            if args.base_image:
                sandbox_info = prepare_base_image(
                    args.base_image,
                    pull=args.pull_base_image,
                )

            internal_result = tmpdir / "result.json"
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
            if args.base_image:
                command.extend(["--image-override", args.base_image])

            completed = subprocess.run(command, text=True, capture_output=True)

            # The pretty transcript is student-safe rubric feedback. Presigned URLs,
            # generated hidden variables, and internal JSON metadata are never printed.
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=sys.stderr)

            if completed.returncode in (0, 2) and internal_result.is_file():
                payload = json.loads(internal_result.read_text(encoding="utf-8"))
                metadata = payload.setdefault("metadata", {})
                metadata["worker"] = {
                    "version": WORKER_VERSION,
                    "question_bank_revision": os.environ.get(
                        "QUESTION_BANK_REVISION", "unknown"
                    ),
                    "submission_transport": (
                        "http" if args.submission_url else "local-path"
                    ),
                    "result_transport": "http" if result_url else "local-path",
                    "sandbox_image": sandbox_info,
                }
                publish_result(
                    payload,
                    result_path=result_path,
                    result_url=result_url,
                    timeout_seconds=args.http_timeout_seconds,
                )
                print(
                    f"[worker] Grading completed for {args.lab_id}: "
                    f"{payload.get('score')}/{payload.get('max_score')} "
                    f"({'PASS' if payload.get('passed') else 'FAIL'})"
                )
                return 0

            payload = error_payload(
                args.lab_id,
                "Question-bank runner failed before producing a grading result.",
                runner_returncode=completed.returncode,
                runner_stdout=tail(completed.stdout),
                runner_stderr=tail(completed.stderr),
            )
            publish_result(
                payload,
                result_path=result_path,
                result_url=result_url,
                timeout_seconds=args.http_timeout_seconds,
            )
            print(
                f"[worker] Infrastructure failure while grading {args.lab_id}",
                file=sys.stderr,
            )
            return 1

    except WorkerError as exc:
        payload = error_payload(args.lab_id, str(exc))
        # If the result target itself is broken, there is nowhere else to persist
        # the structured error; the ECS task log remains the final diagnostic.
        try:
            if bool(result_path) ^ bool(result_url):
                publish_result(
                    payload,
                    result_path=result_path,
                    result_url=result_url,
                    timeout_seconds=max(1, getattr(args, "http_timeout_seconds", 30)),
                )
        except Exception as publish_exc:  # pragma: no cover - last-resort logging
            print(f"ERROR: unable to publish worker error result: {publish_exc}", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        payload = error_payload(args.lab_id, f"Unexpected worker failure: {type(exc).__name__}")
        try:
            if bool(result_path) ^ bool(result_url):
                publish_result(
                    payload,
                    result_path=result_path,
                    result_url=result_url,
                    timeout_seconds=max(1, getattr(args, "http_timeout_seconds", 30)),
                )
        except Exception:
            pass
        print(f"ERROR: unexpected worker failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
