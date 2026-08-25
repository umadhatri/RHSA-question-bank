from __future__ import annotations

import importlib.util
import io
import tarfile
from pathlib import Path


def load_grade(path: Path):
    spec = importlib.util.spec_from_file_location(f"test_{path.parent.name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.grade


def add_file(tar: tarfile.TarFile, name: str, content: bytes | str, mode: int = 0o644, uid: int = 0, gid: int = 0):
    data = content.encode() if isinstance(content, str) else content
    info = tarfile.TarInfo(name.lstrip("/"))
    info.size = len(data)
    info.mode = mode
    info.uid = uid
    info.gid = gid
    tar.addfile(info, io.BytesIO(data))


def add_dir(tar: tarfile.TarFile, name: str, mode: int = 0o755, uid: int = 0, gid: int = 0):
    info = tarfile.TarInfo(name.lstrip("/").rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = uid
    info.gid = gid
    tar.addfile(info)
