#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grader.validation import (  # noqa: E402
    ValidationError,
    load_yaml,
    validate_grader_signature,
    validate_lab_config,
)

SCHEMA = ROOT / "schemas" / "lab.schema.json"
REQUIRED = ("question.md", "lab.yaml", "setup.sh", "grader.py")


def load_grade_fn(path: Path):
    spec = importlib.util.spec_from_file_location(f"validate_{path.parent.name}", path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "grade"):
        raise ValidationError(f"{path} does not define grade()")
    return module.grade


def validate_lab_dir(path: Path) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED:
        if not (path / name).is_file():
            errors.append(f"missing required file: {name}")
    if errors:
        return errors

    try:
        lab = load_yaml(path / "lab.yaml")
        validate_lab_config(lab, SCHEMA)
        if path.name != lab["id"]:
            errors.append(f"directory name {path.name!r} must equal lab id {lab['id']!r}")
        grade_fn = load_grade_fn(path / "grader.py")
        validate_grader_signature(grade_fn)
        if not (path / "question.md").read_text(encoding="utf-8").strip():
            errors.append("question.md is empty")
        if not (path / "setup.sh").read_text(encoding="utf-8").startswith("#!/usr/bin/env bash"):
            errors.append("setup.sh must start with #!/usr/bin/env bash")
    except Exception as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate every RHSA lab in the repository.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    course = load_yaml(ROOT / "course.yaml")
    discovered: list[Path] = []
    failures = 0

    for module in course.get("modules", []):
        module_path = ROOT / module["path"]
        if not module_path.is_dir():
            print(f"[FAIL] module {module['id']}: missing path {module_path.relative_to(ROOT)}")
            failures += 1
            continue
        for candidate in sorted(module_path.iterdir()):
            if candidate.is_dir() and (candidate / "lab.yaml").exists():
                discovered.append(candidate)

    if not discovered:
        print("[FAIL] no lab questions discovered")
        return 1

    for lab_dir in discovered:
        errors = validate_lab_dir(lab_dir)
        if errors:
            failures += 1
            print(f"[FAIL] {lab_dir.name}")
            for error in errors:
                print(f"       - {error}")
        elif not args.quiet:
            print(f"[PASS] {lab_dir.name}")

    if failures:
        print(f"\nRepository validation failed: {failures} item(s) need attention.")
        return 1
    print(f"\nRepository validation passed: {len(discovered)} lab(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
