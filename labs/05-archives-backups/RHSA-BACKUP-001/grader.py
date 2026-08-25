from __future__ import annotations

import io
import tarfile
from typing import Any

from grader.api import GradeBook, SnapshotSet


def inspect_archive(data: bytes | None) -> tuple[bool, dict[str, bytes], set[str]]:
    if data is None:
        return False, {}, set()
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            files: dict[str, bytes] = {}
            dirs: set[str] = set()
            for member in archive.getmembers():
                name = member.name
                while name.startswith("./"):
                    name = name[2:]
                name = name.rstrip("/")
                if not name or name == ".":
                    continue
                if name.startswith("/") or ".." in name.split("/"):
                    return False, {}, set()
                if member.isdir():
                    dirs.add(name)
                elif member.isfile():
                    handle = archive.extractfile(member)
                    files[name] = handle.read() if handle else b""
            return True, files, dirs
    except (tarfile.TarError, OSError):
        return False, {}, set()


def expected_files(token: str) -> dict[str, bytes]:
    return {
        f"README_{token}.txt": f"Training backup {token}\n".encode(),
        "configs/app.conf": b"listen_port=8443\nmode=training\n",
        "data/users.csv": b"user,role\nalice,admin\nbob,operator\n",
        "data/nested/state.txt": f"nested={token}\n".encode(),
        ".backup_meta": f"secret-marker={token}\n".encode(),
    }


def grade(lab: dict[str, Any], context: dict[str, Any], snapshots: SnapshotSet) -> dict[str, Any]:
    book = GradeBook(lab)
    token = context["variables"]["TEST_TOKEN"]
    dst = f"/var/backups/training_{token}"
    archive_path = f"{dst}/backup_{token}.tar.gz"
    expected = expected_files(token)

    first_snapshot = snapshots["after_first"]
    second_snapshot = snapshots["after_second"]
    first_data = first_snapshot.read_bytes(archive_path)
    second_data = second_snapshot.read_bytes(archive_path)
    valid, files, _dirs = inspect_archive(first_data)
    second_valid, second_files, _ = inspect_archive(second_data)

    book.check("syntax", context.get("syntax_ok", False), "Bash syntax is valid.", "Bash syntax validation failed.")
    first_rc = int(context.get("first_run", {}).get("returncode", 1))
    book.check("first_run_exit", first_rc == 0 and not context.get("first_run", {}).get("timed_out", False),
               "The first execution exited successfully.", f"The first execution returned exit code {first_rc}.")
    book.check("destination_created", first_snapshot.is_dir(dst), "The destination directory exists.", "The destination directory was not created.")
    book.check("archive_created", first_data is not None, "The requested archive was created.", "The requested archive file was not created.")
    book.check("valid_gzip_tar", valid, "The output is a readable gzip-compressed tar archive with relative paths.",
               "The output is not a valid gzip tar archive or contains unsafe/absolute paths.")

    required_present = sum(1 for name in expected if name in files)
    book.award("required_entries", round(20 * required_present / len(expected)), required_present == len(expected),
               f"Archive contains {required_present} of {len(expected)} required files.")
    contents_correct = sum(1 for name, content in expected.items() if files.get(name) == content)
    book.award("file_contents", round(20 * contents_correct / len(expected)), contents_correct == len(expected),
               f"Correct contents for {contents_correct} of {len(expected)} required files.")
    book.check("no_extra_entries", valid and set(files) == set(expected), "The archive contains no unrelated regular files.",
               "The archive contains missing or unrelated regular files.")

    second_rc = int(context.get("second_run", {}).get("returncode", 1))
    backup_files_second = [p for p in second_snapshot.paths_under(dst) if second_snapshot.is_file(p)] if second_snapshot.is_dir(dst) else []
    idem = (
        first_rc == 0
        and second_rc == 0
        and valid
        and second_valid
        and files == expected
        and second_files == expected
        and backup_files_second == [archive_path]
        and not context.get("second_run", {}).get("timed_out", False)
    )
    book.check("idempotency", idem, "Repeated execution preserves one correct requested archive and creates no extra backup files.",
               "The repeat execution failed, changed the archive contents, or created additional backup files.")
    return book.finalize()
