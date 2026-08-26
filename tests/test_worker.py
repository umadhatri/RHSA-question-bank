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
