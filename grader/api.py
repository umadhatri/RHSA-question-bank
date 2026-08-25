from __future__ import annotations

import tarfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterator, Mapping


@dataclass(frozen=True)
class PasswdEntry:
    name: str
    uid: int
    gid: int
    home: str
    shell: str


@dataclass(frozen=True)
class GroupEntry:
    name: str
    gid: int
    members: tuple[str, ...]


class RootfsSnapshot:
    """Read-only inspection of a Docker-exported root filesystem tarball."""

    def __init__(self, tar_path: str):
        self._tar = tarfile.open(tar_path, "r")
        self._members = {self._normalize(m.name): m for m in self._tar.getmembers()}
        self._passwd_cache: dict[str, PasswdEntry] | None = None
        self._group_cache: dict[str, GroupEntry] | None = None

    @staticmethod
    def _normalize(path: str) -> str:
        p = str(PurePosixPath("/" + path.lstrip("/")))
        return p.lstrip("/")

    def close(self) -> None:
        self._tar.close()

    def __enter__(self) -> "RootfsSnapshot":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def exists(self, path: str) -> bool:
        return self._normalize(path) in self._members

    def is_dir(self, path: str) -> bool:
        member = self._members.get(self._normalize(path))
        return bool(member and member.isdir())

    def is_file(self, path: str) -> bool:
        member = self._members.get(self._normalize(path))
        return bool(member and member.isfile())

    def paths_under(self, path: str) -> tuple[str, ...]:
        """Return normalized snapshot paths strictly below *path*."""
        base = self._normalize(path).rstrip("/")
        prefix = f"{base}/" if base else ""
        return tuple(
            f"/{name}" for name in sorted(self._members)
            if name.startswith(prefix) and name != base
        )

    def mode(self, path: str) -> int | None:
        member = self._members.get(self._normalize(path))
        return member.mode if member else None

    def uid(self, path: str) -> int | None:
        member = self._members.get(self._normalize(path))
        return member.uid if member else None

    def gid(self, path: str) -> int | None:
        member = self._members.get(self._normalize(path))
        return member.gid if member else None

    def read_bytes(self, path: str) -> bytes | None:
        member = self._members.get(self._normalize(path))
        if not member or not member.isfile():
            return None
        extracted = self._tar.extractfile(member)
        return extracted.read() if extracted else None

    def read_text(self, path: str, encoding: str = "utf-8") -> str | None:
        raw = self.read_bytes(path)
        return raw.decode(encoding, errors="replace") if raw is not None else None

    def passwd_entries(self) -> dict[str, PasswdEntry]:
        if self._passwd_cache is not None:
            return self._passwd_cache

        text = self.read_text("/etc/passwd") or ""
        result: dict[str, PasswdEntry] = {}
        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 7:
                continue
            name, _, uid, gid, _, home, shell = parts[:7]
            try:
                result[name] = PasswdEntry(name, int(uid), int(gid), home, shell)
            except ValueError:
                continue
        self._passwd_cache = result
        return result

    def group_entries(self) -> dict[str, GroupEntry]:
        if self._group_cache is not None:
            return self._group_cache

        text = self.read_text("/etc/group") or ""
        result: dict[str, GroupEntry] = {}
        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 4:
                continue
            name, _, gid, members = parts[:4]
            try:
                result[name] = GroupEntry(
                    name=name,
                    gid=int(gid),
                    members=tuple(x for x in members.split(",") if x),
                )
            except ValueError:
                continue
        self._group_cache = result
        return result

    def user(self, username: str) -> PasswdEntry | None:
        return self.passwd_entries().get(username)

    def group(self, groupname: str) -> GroupEntry | None:
        return self.group_entries().get(groupname)


class SnapshotSet(Mapping[str, RootfsSnapshot]):
    """Named lifecycle snapshots exposed to a lab grader.

    Contract v1 currently guarantees:
      - ``after_first``: filesystem state after the first submission run.
      - ``after_second``: filesystem state after the repeat/idempotency run.
    """

    REQUIRED = ("after_first", "after_second")

    def __init__(self, paths: Mapping[str, str]):
        missing = [name for name in self.REQUIRED if name not in paths]
        if missing:
            raise ValueError(f"Missing required snapshots: {', '.join(missing)}")
        self._snapshots = {name: RootfsSnapshot(path) for name, path in paths.items()}

    def __getitem__(self, key: str) -> RootfsSnapshot:
        return self._snapshots[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._snapshots)

    def __len__(self) -> int:
        return len(self._snapshots)

    def close(self) -> None:
        for snapshot in self._snapshots.values():
            snapshot.close()

    def __enter__(self) -> "SnapshotSet":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class GradeBook:
    """Build criterion-level results from the rubric in lab.yaml."""

    def __init__(self, lab_config: dict[str, Any]):
        criteria = lab_config.get("grading", {}).get("criteria", [])
        self._criteria = {item["id"]: item for item in criteria}
        self._order = [item["id"] for item in criteria]
        self._results: dict[str, dict[str, Any]] = {}

    def _require(self, criterion_id: str) -> int:
        if criterion_id in self._results:
            raise ValueError(f"Criterion graded more than once: {criterion_id}")
        if criterion_id not in self._criteria:
            raise KeyError(f"Unknown rubric criterion: {criterion_id}")
        return int(self._criteria[criterion_id]["points"])

    def check(self, criterion_id: str, passed: bool, success: str, failure: str) -> None:
        maximum = self._require(criterion_id)
        self._results[criterion_id] = {
            "id": criterion_id,
            "passed": bool(passed),
            "points": maximum if passed else 0,
            "max_points": maximum,
            "feedback": success if passed else failure,
        }

    def award(self, criterion_id: str, points: int, passed: bool, feedback: str) -> None:
        maximum = self._require(criterion_id)
        points = max(0, min(int(points), maximum))
        self._results[criterion_id] = {
            "id": criterion_id,
            "passed": bool(passed),
            "points": points,
            "max_points": maximum,
            "feedback": feedback,
        }

    def finalize(self) -> dict[str, Any]:
        ordered: list[dict[str, Any]] = []
        for criterion_id in self._order:
            item = self._criteria[criterion_id]
            if criterion_id in self._results:
                ordered.append(self._results[criterion_id])
            else:
                maximum = int(item["points"])
                ordered.append(
                    {
                        "id": criterion_id,
                        "passed": False,
                        "points": 0,
                        "max_points": maximum,
                        "feedback": "Criterion was not evaluated by the grader.",
                    }
                )

        score = sum(item["points"] for item in ordered)
        maximum = sum(item["max_points"] for item in ordered)
        return {"score": score, "max_score": maximum, "tests": ordered}
