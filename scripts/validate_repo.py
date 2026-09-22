#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grader.validation import (  # noqa: E402
    ValidationError,
    discover_lab_id_locations,
    load_yaml,
    validate_grader_signature,
    validate_lab_config,
)

SCHEMA = ROOT / "schemas" / "lab.schema.json"
CATALOGS_FILE = ROOT / "catalogs.yaml"
LEGACY_COURSE_FILE = ROOT / "course.yaml"
REQUIRED = ("question.md", "lab.yaml", "setup.sh", "grader.py")


@dataclass(frozen=True)
class Catalog:
    marketplace_lab_id: str
    title: str
    manifest_path: Path
    prefixes: tuple[str, ...]
    course: dict[str, Any]


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


def _normalized_prefixes(value: Any, *, catalog_id: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValidationError(
            f"catalog {catalog_id!r} must declare a non-empty lab_id_prefixes list"
        )

    prefixes = tuple(str(item).strip() for item in value if str(item).strip())
    if not prefixes:
        raise ValidationError(
            f"catalog {catalog_id!r} must declare at least one non-empty lab ID prefix"
        )
    if len(set(prefixes)) != len(prefixes):
        raise ValidationError(f"catalog {catalog_id!r} contains duplicate lab ID prefixes")
    return prefixes


def load_catalogs() -> list[Catalog]:
    # Backward-compatible fallback for older checkouts.
    if not CATALOGS_FILE.is_file():
        if not LEGACY_COURSE_FILE.is_file():
            raise ValidationError("neither catalogs.yaml nor course.yaml exists")
        course = load_yaml(LEGACY_COURSE_FILE)
        return [
            Catalog(
                marketplace_lab_id="linux-sysadmin-lab",
                title=str(course.get("title") or "Linux System Administration"),
                manifest_path=LEGACY_COURSE_FILE,
                prefixes=("TUPE-", "RHSA-"),
                course=course,
            )
        ]

    registry = load_yaml(CATALOGS_FILE)
    if int(registry.get("contract_version") or 0) != 1:
        raise ValidationError("catalogs.yaml contract_version must be 1")

    raw_catalogs = registry.get("catalogs")
    if not isinstance(raw_catalogs, list) or not raw_catalogs:
        raise ValidationError("catalogs.yaml must contain a non-empty catalogs list")

    result: list[Catalog] = []
    seen_ids: set[str] = set()
    seen_manifests: set[Path] = set()
    prefix_owners: dict[str, str] = {}

    for item in raw_catalogs:
        if not isinstance(item, dict):
            raise ValidationError("catalog entries must be mappings")

        catalog_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or catalog_id).strip()
        manifest_raw = str(item.get("manifest") or "").strip()

        if not catalog_id:
            raise ValidationError("catalog entry is missing id")
        if catalog_id in seen_ids:
            raise ValidationError(f"duplicate catalog id: {catalog_id}")
        seen_ids.add(catalog_id)

        if not manifest_raw or Path(manifest_raw).is_absolute():
            raise ValidationError(
                f"catalog {catalog_id!r} must use a relative manifest path"
            )

        manifest = (ROOT / manifest_raw).resolve()
        try:
            manifest.relative_to(ROOT)
        except ValueError as exc:
            raise ValidationError(
                f"catalog {catalog_id!r} manifest escapes repository root"
            ) from exc

        if not manifest.is_file():
            raise ValidationError(
                f"catalog {catalog_id!r} manifest does not exist: {manifest_raw}"
            )
        if manifest in seen_manifests:
            raise ValidationError(
                f"manifest {manifest_raw!r} is assigned to more than one catalog"
            )
        seen_manifests.add(manifest)

        prefixes = _normalized_prefixes(
            item.get("lab_id_prefixes"),
            catalog_id=catalog_id,
        )
        for prefix in prefixes:
            previous = prefix_owners.get(prefix)
            if previous is not None:
                raise ValidationError(
                    f"lab ID prefix {prefix!r} belongs to both "
                    f"{previous!r} and {catalog_id!r}"
                )
            prefix_owners[prefix] = catalog_id

        course = load_yaml(manifest)
        modules = course.get("modules")
        if not isinstance(modules, list) or not modules:
            raise ValidationError(
                f"catalog {catalog_id!r} manifest contains no modules"
            )

        result.append(
            Catalog(
                marketplace_lab_id=catalog_id,
                title=title,
                manifest_path=manifest,
                prefixes=prefixes,
                course=course,
            )
        )

    return result


def _catalog_for_lab_id(lab_id: str, catalogs: list[Catalog]) -> Catalog | None:
    matches = [
        catalog
        for catalog in catalogs
        if lab_id.startswith(catalog.prefixes)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate every CyberRange question-bank lab in the repository."
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        catalogs = load_catalogs()
    except Exception as exc:
        print(f"[FAIL] catalog registry: {exc}")
        return 1

    discovered: list[tuple[Path, str, Catalog]] = []
    failures = 0

    # Scan the entire labs tree first. This catches stale copies and also proves
    # that every lab belongs to exactly one registered product catalog.
    all_locations = discover_lab_id_locations(ROOT / "labs")

    for lab_id, paths in sorted(all_locations.items()):
        if len(paths) > 1:
            failures += 1
            print(f"[FAIL] duplicate lab id: {lab_id}")
            for path in paths:
                print(f"       - {path.relative_to(ROOT)}")

        owner = _catalog_for_lab_id(lab_id, catalogs)
        if owner is None:
            failures += 1
            print(
                f"[FAIL] unowned or ambiguous lab id: {lab_id} "
                "does not match exactly one catalog prefix set"
            )

    configured_module_paths: dict[Path, tuple[str, Catalog]] = {}

    for catalog in catalogs:
        for module in catalog.course.get("modules", []):
            if not isinstance(module, dict):
                failures += 1
                print(
                    f"[FAIL] catalog {catalog.marketplace_lab_id}: "
                    "module entry must be a mapping"
                )
                continue

            module_id = str(module.get("id") or "").strip()
            path_raw = str(module.get("path") or "").strip()

            if not module_id or not path_raw:
                failures += 1
                print(
                    f"[FAIL] catalog {catalog.marketplace_lab_id}: "
                    "module requires id and path"
                )
                continue

            module_path = (ROOT / path_raw).resolve()
            previous = configured_module_paths.get(module_path)
            if previous is not None:
                failures += 1
                print(
                    f"[FAIL] module path {path_raw!r} is registered more than once: "
                    f"{previous[1].marketplace_lab_id}/{previous[0]} and "
                    f"{catalog.marketplace_lab_id}/{module_id}"
                )
                continue

            configured_module_paths[module_path] = (module_id, catalog)

    for lab_paths in all_locations.values():
        for lab_path in lab_paths:
            module_path = lab_path.parent.resolve()
            if module_path not in configured_module_paths:
                failures += 1
                print(
                    f"[FAIL] unlisted lab module: {lab_path.relative_to(ROOT)} "
                    "is not under any catalog manifest module path"
                )

    for module_path, (module_id, catalog) in configured_module_paths.items():
        if not module_path.is_dir():
            print(
                f"[FAIL] catalog {catalog.marketplace_lab_id} module {module_id}: "
                f"missing path {module_path.relative_to(ROOT)}"
            )
            failures += 1
            continue

        for candidate in sorted(module_path.iterdir()):
            if not (candidate.is_dir() and (candidate / "lab.yaml").exists()):
                continue

            lab_id = candidate.name
            if not lab_id.startswith(catalog.prefixes):
                failures += 1
                print(
                    f"[FAIL] {lab_id}: module belongs to catalog "
                    f"{catalog.marketplace_lab_id!r}, but lab ID does not match "
                    f"allowed prefixes {catalog.prefixes!r}"
                )

            discovered.append((candidate, module_id, catalog))

    if not discovered:
        print("[FAIL] no lab questions discovered")
        return 1

    for lab_dir, module_id, catalog in discovered:
        errors = validate_lab_dir(lab_dir)
        if not errors:
            lab = load_yaml(lab_dir / "lab.yaml")
            if lab.get("module") != module_id:
                errors.append(
                    f"lab module {lab.get('module')!r} does not match "
                    f"catalog module {module_id!r}"
                )

            owner = _catalog_for_lab_id(str(lab.get("id") or ""), catalogs)
            if owner is None or owner.marketplace_lab_id != catalog.marketplace_lab_id:
                errors.append(
                    f"lab ID ownership does not match catalog "
                    f"{catalog.marketplace_lab_id!r}"
                )

        if errors:
            failures += 1
            print(f"[FAIL] {lab_dir.name}")
            for error in errors:
                print(f"       - {error}")
        elif not args.quiet:
            print(
                f"[PASS] {lab_dir.name} "
                f"[catalog={catalog.marketplace_lab_id}]"
            )

    if failures:
        print(f"\nRepository validation failed: {failures} item(s) need attention.")
        return 1

    counts: dict[str, int] = {}
    for _, _, catalog in discovered:
        counts[catalog.marketplace_lab_id] = counts.get(catalog.marketplace_lab_id, 0) + 1

    summary = ", ".join(
        f"{catalog.marketplace_lab_id}={counts.get(catalog.marketplace_lab_id, 0)}"
        for catalog in catalogs
    )

    print(
        f"\nRepository validation passed: {len(discovered)} lab(s) "
        f"across {len(catalogs)} catalog(s): {summary}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
