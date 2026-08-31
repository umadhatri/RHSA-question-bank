from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from worker.run_job import (
    WorkerError,
    download_submission,
    ecr_registry_region,
    parse_base_image_map,
    resolve_base_image,
    resolve_lab,
    upload_result,
)

ROOT = Path(__file__).resolve().parents[1]


class _ObjectStoreHandler(BaseHTTPRequestHandler):
    submission = b"#!/bin/bash\necho hello\n"
    uploaded: bytes | None = None

    def do_GET(self):  # noqa: N802
        if self.path != "/submission.sh":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/x-shellscript")
        self.send_header("Content-Length", str(len(self.submission)))
        self.end_headers()
        self.wfile.write(self.submission)

    def do_PUT(self):  # noqa: N802
        if self.path != "/result.json":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        type(self).uploaded = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()

    def log_message(self, _format, *_args):
        return


class GradingWorkerTests(unittest.TestCase):
    def test_resolves_existing_lab_by_declared_id(self):
        lab = resolve_lab(ROOT, "RHSA-USERS-001")
        self.assertEqual(lab.name, "RHSA-USERS-001")
        self.assertEqual(lab.parent.name, "03-users-groups")

    def test_rejects_unknown_lab_id(self):
        with self.assertRaises(WorkerError):
            resolve_lab(ROOT, "RHSA-NOT-REAL-999")

    def test_rejects_duplicate_lab_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for module in ("01-old", "02-current"):
                lab = root / "labs" / module / "RHSA-DUP-001"
                lab.mkdir(parents=True)
                (lab / "lab.yaml").write_text(
                    "id: RHSA-DUP-001\ntitle: Duplicate\n", encoding="utf-8"
                )
            with self.assertRaises(WorkerError):
                resolve_lab(root, "RHSA-DUP-001")

    def test_resolves_lab_image_through_immutable_map(self):
        lab = resolve_lab(ROOT, "RHSA-SUDO-001")
        logical = "cyberrange/rhsa-base:0.4"
        immutable = (
            "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
            "cyberrange/rhsa-base@sha256:"
            "14482ef29550d70e12f4e2632ba7029911de10df33ca918f09042281a5557e47"
        )

        resolved, source = resolve_base_image(
            lab,
            explicit_image=None,
            image_map_json=json.dumps({logical: immutable}),
        )

        self.assertEqual(resolved, immutable)
        self.assertEqual(source, "image-map")

    def test_explicit_base_image_wins_over_image_map(self):
        lab = resolve_lab(ROOT, "RHSA-SUDO-001")

        resolved, source = resolve_base_image(
            lab,
            explicit_image="cyberrange/test-base:explicit",
            image_map_json=json.dumps(
                {
                    "cyberrange/rhsa-base:0.4":
                        "cyberrange/test-base:mapped"
                }
            ),
        )

        self.assertEqual(
            resolved,
            "cyberrange/test-base:explicit",
        )
        self.assertEqual(source, "explicit")

    def test_without_override_or_map_runner_uses_lab_config(self):
        lab = resolve_lab(ROOT, "RHSA-SUDO-001")

        resolved, source = resolve_base_image(
            lab,
            explicit_image=None,
            image_map_json=None,
        )

        self.assertIsNone(resolved)
        self.assertEqual(source, "lab-config")

    def test_missing_immutable_image_mapping_fails_closed(self):
        lab = resolve_lab(ROOT, "RHSA-SCHED-001")

        with self.assertRaises(WorkerError):
            resolve_base_image(
                lab,
                explicit_image=None,
                image_map_json=json.dumps(
                    {
                        "cyberrange/rhsa-base:0.3":
                            "example.invalid/base@sha256:abc"
                    }
                ),
            )

    def test_malformed_image_map_is_rejected(self):
        with self.assertRaises(WorkerError):
            parse_base_image_map("{not-json")

        with self.assertRaises(WorkerError):
            parse_base_image_map('["not", "an", "object"]')

    def test_all_production_lab_images_can_be_mapped(self):
        image_map = {
            "cyberrange/rhsa-base:0.3": (
                "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
                "cyberrange/rhsa-base@sha256:"
                "0f59aef8f7f19ee5c7215b70e65d019e02e7205c2238627376ae859fd2658a1f"
            ),
            "cyberrange/rhsa-base:0.4": (
                "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
                "cyberrange/rhsa-base@sha256:"
                "14482ef29550d70e12f4e2632ba7029911de10df33ca918f09042281a5557e47"
            ),
            "cyberrange/rhsa-base:0.5": (
                "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
                "cyberrange/rhsa-base@sha256:"
                "c643f41705aa6bd552c9537821da3f62095082d788c8ef87986755eace618c26"
            ),
            "cyberrange/rhsa-base:0.6": (
                "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
                "cyberrange/rhsa-base@sha256:"
                "8ea6da64bc13b2eaa33468fd53dfa54ae089cd8c3b6213bdc7cf5e35e5b3378d"
            ),
            "cyberrange/rhsa-base:0.7": (
                "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
                "cyberrange/rhsa-base@sha256:"
                "680a15fdc0b2978b90b2a5fc55615ed9114a2879532ad74907363984f17d6e60"
            ),
        }

        lab_ids = (
            "RHSA-SHELL-001",
            "RHSA-FILE-001",
            "RHSA-USERS-001",
            "RHSA-TEXT-001",
            "RHSA-BACKUP-001",
            "RHSA-SUDO-001",
            "RHSA-PROC-001",
            "RHSA-PKG-001",
            "RHSA-SSH-001",
            "RHSA-SCHED-001",
        )

        encoded = json.dumps(image_map)

        for lab_id in lab_ids:
            with self.subTest(lab_id=lab_id):
                lab = resolve_lab(ROOT, lab_id)
                resolved, source = resolve_base_image(
                    lab,
                    explicit_image=None,
                    image_map_json=encoded,
                )

                self.assertIn("@sha256:", resolved)
                self.assertEqual(source, "image-map")

    def test_remote_http_submission_and_result_transport(self):
        _ObjectStoreHandler.uploaded = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ObjectStoreHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory() as tmp:
                destination = Path(tmp) / "submission.sh"
                download_submission(f"{base}/submission.sh", destination)
                self.assertEqual(destination.read_bytes(), _ObjectStoreHandler.submission)

                payload = {"score": 100, "passed": True}
                upload_result(f"{base}/result.json", payload)
                self.assertIsNotNone(_ObjectStoreHandler.uploaded)
                self.assertEqual(json.loads(_ObjectStoreHandler.uploaded), payload)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_remote_submission_size_limit_is_enforced(self):
        _ObjectStoreHandler.uploaded = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ObjectStoreHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory() as tmp:
                destination = Path(tmp) / "submission.sh"
                with self.assertRaises(WorkerError):
                    download_submission(
                        f"{base}/submission.sh",
                        destination,
                        max_bytes=8,
                    )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_ecr_registry_region_is_detected(self):
        image = (
            "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
            "cyberrange/rhsa-base:0.3"
        )
        self.assertEqual(
            ecr_registry_region(image),
            ("766363046973.dkr.ecr.ap-south-1.amazonaws.com", "ap-south-1"),
        )
        self.assertIsNone(ecr_registry_region("cyberrange/rhsa-base:0.3"))


if __name__ == "__main__":
    unittest.main()
