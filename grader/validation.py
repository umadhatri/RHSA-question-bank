from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


class ValidationError(RuntimeError):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValidationError(f"Expected a YAML mapping in {path}")
    return data


def validate_lab_config(lab: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(lab), key=lambda e: list(e.absolute_path))
    if errors:
        formatted = []
        for error in errors:
            where = ".".join(str(x) for x in error.absolute_path) or "<root>"
            formatted.append(f"{where}: {error.message}")
        raise ValidationError("lab.yaml schema validation failed:\n  - " + "\n  - ".join(formatted))

    criteria = lab["grading"]["criteria"]
    ids = [item["id"] for item in criteria]
    if len(ids) != len(set(ids)):
        raise ValidationError("grading.criteria contains duplicate criterion IDs")

    rubric_total = sum(int(item["points"]) for item in criteria)
    declared_total = int(lab["grading"]["total_points"])
    if rubric_total != declared_total:
        raise ValidationError(
            f"Rubric criteria total {rubric_total}, but grading.total_points is {declared_total}"
        )

    pass_score = int(lab["grading"].get("pass_score", declared_total))
    if pass_score > declared_total:
        raise ValidationError("grading.pass_score cannot exceed grading.total_points")

    for name, spec in lab.get("variables", {}).items():
        kind = spec.get("type")
        if kind in {"random_int", "random_ipv4"}:
            minimum = int(spec.get("min", 1))
            maximum = int(spec.get("max", 100 if kind == "random_int" else 254))
            if minimum > maximum:
                raise ValidationError(f"variables.{name}: min cannot exceed max")
            if kind == "random_ipv4" and (minimum < 1 or maximum > 254):
                raise ValidationError(f"variables.{name}: random_ipv4 host range must be within 1..254")


def validate_grader_signature(grade_fn: Any) -> None:
    signature = inspect.signature(grade_fn)
    names = list(signature.parameters)
    if names != ["lab", "context", "snapshots"]:
        raise ValidationError(
            "grader.py grade() must use the contract-v1 signature: "
            "grade(lab, context, snapshots)"
        )


def discover_lab_id_locations(labs_root: Path) -> dict[str, list[Path]]:
    """Return every declared lab ID under labs/*/*, including unlisted modules."""
    locations: dict[str, list[Path]] = {}
    if not labs_root.is_dir():
        return locations
    for lab_yaml in sorted(labs_root.glob("*/*/lab.yaml")):
        try:
            data = load_yaml(lab_yaml)
            lab_id = str(data.get("id") or lab_yaml.parent.name)
        except Exception:
            # Normal per-lab validation will report malformed YAML. Falling back
            # to the directory name still lets us detect obvious stale copies.
            lab_id = lab_yaml.parent.name
        locations.setdefault(lab_id, []).append(lab_yaml.parent)
    return locations
