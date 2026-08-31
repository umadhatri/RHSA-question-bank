from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import yaml

from grader.api import SnapshotSet


ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "labs" / "09-ssh-access" / "RHSA-SSH-001"

USERNAME = "student_123456"
UID = 2000
GID = 2000
HOME = f"/home/{USERNAME}"

SSH_DIR = f"{HOME}/.ssh"
AUTHORIZED_KEYS = f"{SSH_DIR}/authorized_keys"

SOURCE_KEY = "/opt/cyberrange/keys/access_key.pub"
SSHD_CONFIG = "/etc/ssh/sshd_config"

EXISTING_KEY = (
    "ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAIExistingSyntheticKey "
    "existing-test\n"
)

SUPPLIED_KEY = (
    "ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAISuppliedSyntheticKey "
    "supplied-test\n"
)

SSHD_CONFIG_CONTENT = (
    "# synthetic sshd configuration\n"
    "AuthorizedKeysFile .ssh/authorized_keys\n"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def add_dir(
    tar: tarfile.TarFile,
    name: str,
    *,
    mode: int = 0o755,
    uid: int = 0,
    gid: int = 0,
):
    info = tarfile.TarInfo(
        name.lstrip("/").rstrip("/") + "/"
    )
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = uid
    info.gid = gid
    tar.addfile(info)


def add_file(
    tar: tarfile.TarFile,
    name: str,
    content: str,
    *,
    mode: int = 0o644,
    uid: int = 0,
    gid: int = 0,
):
    data = content.encode()

    info = tarfile.TarInfo(name.lstrip("/"))
    info.size = len(data)
    info.mode = mode
    info.uid = uid
    info.gid = gid

    tar.addfile(info, io.BytesIO(data))


def snapshot(
    path: Path,
    *,
    authorized_keys: str | None = None,
    ssh_dir_mode: int = 0o700,
    authorized_keys_mode: int = 0o600,
    user_uid: int = UID,
    user_gid: int = GID,
    user_home: str = HOME,
    source_key: str = SUPPLIED_KEY,
    sshd_config: str = SSHD_CONFIG_CONTENT,
):
    if authorized_keys is None:
        authorized_keys = EXISTING_KEY + SUPPLIED_KEY

    with tarfile.open(path, "w") as tar:
        add_dir(tar, "/etc")
        add_dir(tar, "/etc/ssh")
        add_dir(
            tar,
            "/etc/ssh/sshd_config.d",
            mode=0o700,
            uid=0,
            gid=0,
        )

        add_dir(tar, "/home")
        add_dir(
            tar,
            HOME,
            uid=UID,
            gid=GID,
        )

        add_dir(
            tar,
            SSH_DIR,
            mode=ssh_dir_mode,
            uid=UID,
            gid=GID,
        )

        add_dir(tar, "/opt")
        add_dir(tar, "/opt/cyberrange")
        add_dir(tar, "/opt/cyberrange/keys")

        add_file(
            tar,
            "/etc/passwd",
            (
                "root:x:0:0:root:/root:/bin/bash\n"
                f"{USERNAME}:x:{user_uid}:{user_gid}::"
                f"{user_home}:/bin/bash\n"
            ),
        )

        add_file(
            tar,
            "/etc/group",
            (
                "root:x:0:\n"
                f"{USERNAME}:x:{GID}:\n"
            ),
        )

        add_file(
            tar,
            SSHD_CONFIG,
            sshd_config,
            mode=0o600,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            SOURCE_KEY,
            source_key,
            mode=0o644,
            uid=0,
            gid=0,
        )

        add_file(
            tar,
            AUTHORIZED_KEYS,
            authorized_keys,
            mode=authorized_keys_mode,
            uid=UID,
            gid=GID,
        )


def grader_fn():
    path = LAB_DIR / "grader.py"

    spec = importlib.util.spec_from_file_location(
        "rhsa_ssh_001_test",
        path,
    )

    module = importlib.util.module_from_spec(spec)

    assert spec and spec.loader
    spec.loader.exec_module(module)

    return module.grade


def criterion(result: dict, criterion_id: str) -> dict:
    return next(
        item
        for item in result["tests"]
        if item["id"] == criterion_id
    )


class SSHAccessGraderTests(unittest.TestCase):
    def setUp(self):
        self.lab = yaml.safe_load(
            (LAB_DIR / "lab.yaml").read_text()
        )

        self.context = {
            "syntax_ok": True,
            "variables": {
                "TEST_USERNAME": USERNAME,
            },
            "setup": {
                "stdout": "\n".join(
                    [
                        f"EXPECTED_UID={UID}",
                        f"EXPECTED_GID={GID}",
                        f"EXPECTED_HOME={HOME}",
                        f"EXISTING_KEY_B64={b64(EXISTING_KEY)}",
                        f"SUPPLIED_KEY_B64={b64(SUPPLIED_KEY)}",
                        (
                            "SOURCE_KEY_SHA256="
                            f"{sha256_text(SUPPLIED_KEY)}"
                        ),
                        (
                            "SSHD_CONFIG_SHA256="
                            f"{sha256_text(SSHD_CONFIG_CONTENT)}"
                        ),
                    ]
                )
            },
            "first_run": {
                "returncode": 0,
                "timed_out": False,
            },
            "second_run": {
                "returncode": 0,
                "timed_out": False,
            },
        }

    def grade_snapshots(
        self,
        first_options: dict | None = None,
        second_options: dict | None = None,
    ):
        first_options = first_options or {}

        second_options = (
            first_options
            if second_options is None
            else second_options
        )

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.tar"
            second = Path(tmp) / "second.tar"

            snapshot(first, **first_options)
            snapshot(second, **second_options)

            with SnapshotSet(
                {
                    "after_first": str(first),
                    "after_second": str(second),
                }
            ) as snaps:
                return grader_fn()(
                    self.lab,
                    self.context,
                    snaps,
                )

    def test_correct_ssh_state_scores_100(self):
        result = self.grade_snapshots()

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["max_score"], 100)

    def test_overwriting_existing_key_is_rejected(self):
        result = self.grade_snapshots(
            {
                "authorized_keys": SUPPLIED_KEY,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "existing_key_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "secure_access_state",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )

        self.assertLess(
            result["score"],
            int(self.lab["grading"]["pass_score"]),
        )

    def test_insecure_permissions_are_rejected(self):
        result = self.grade_snapshots(
            {
                "ssh_dir_mode": 0o777,
                "authorized_keys_mode": 0o666,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "permissions",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "secure_access_state",
            )["passed"]
        )

        self.assertLess(
            result["score"],
            int(self.lab["grading"]["pass_score"]),
        )

    def test_duplicate_supplied_key_is_rejected(self):
        result = self.grade_snapshots(
            {
                "authorized_keys": (
                    EXISTING_KEY
                    + SUPPLIED_KEY
                    + SUPPLIED_KEY
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "supplied_key_installed",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "no_extra_keys",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "secure_access_state",
            )["passed"]
        )

    def test_global_sshd_config_modification_is_rejected(self):
        result = self.grade_snapshots(
            {
                "sshd_config": (
                    SSHD_CONFIG_CONTENT
                    + "PermitRootLogin yes\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "global_config_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "secure_access_state",
            )["passed"]
        )

    def test_source_public_key_modification_is_rejected(self):
        result = self.grade_snapshots(
            {
                "source_key": (
                    SUPPLIED_KEY.strip()
                    + " modified\n"
                ),
            }
        )

        self.assertFalse(
            criterion(
                result,
                "source_key_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "secure_access_state",
            )["passed"]
        )

    def test_user_identity_change_is_rejected(self):
        result = self.grade_snapshots(
            {
                "user_uid": UID + 1,
            }
        )

        self.assertFalse(
            criterion(
                result,
                "user_preserved",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "secure_access_state",
            )["passed"]
        )

    def test_second_run_must_preserve_secure_state(self):
        result = self.grade_snapshots(
            {},
            {
                "ssh_dir_mode": 0o777,
            },
        )

        self.assertTrue(
            criterion(
                result,
                "permissions",
            )["passed"]
        )

        self.assertFalse(
            criterion(
                result,
                "idempotency",
            )["passed"]
        )


if __name__ == "__main__":
    unittest.main()
