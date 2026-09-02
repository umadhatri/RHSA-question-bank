from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]


def make_lab(lab_id: str) -> dict:
    return {
        "contract_version": 1,
        "id": lab_id,
        "title": "Contract Test Lab",
        "version": 1,
        "module": "unix-programming-environment",
        "difficulty": "beginner",
        "learning_objectives": [
            "Verify that the requested lab identifier is accepted by the contract."
        ],
        "submission": {
            "filename": "answer.sh",
            "interpreter": "bash",
        },
        "environment": {
            "image": "cyberrange/rhsa-base:0.3",
            "build_context": "docker/base",
            "timeout_seconds": 15,
            "memory": "512m",
            "cpus": 1.0,
            "pids_limit": 128,
            "network": "none",
        },
        "variables": {},
        "execution": {
            "command": [
                "bash",
                "/submission/answer.sh",
            ],
            "repeat_for_idempotency": True,
        },
        "grading": {
            "total_points": 100,
            "pass_score": 70,
            "criteria": [
                {
                    "id": "syntax",
                    "points": 100,
                }
            ],
        },
    }


class TupeLabIdContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads(
            (ROOT / "schemas" / "lab.schema.json").read_text(encoding="utf-8")
        )
        cls.validator = Draft202012Validator(schema)

    def test_existing_rhsa_id_remains_valid(self):
        self.validator.validate(make_lab("RHSA-SHELL-001"))

    def test_tupe_chapter_id_is_valid(self):
        self.validator.validate(make_lab("TUPE-C03-001"))

    def test_invalid_tupe_id_formats_are_rejected(self):
        invalid_ids = (
            "TUPE-C3-001",
            "TUPE-SHELL-001",
            "tupe-C03-001",
            "TUPE-C03/001",
            "../TUPE-C03-001",
        )

        for lab_id in invalid_ids:
            with self.subTest(lab_id=lab_id):
                with self.assertRaises(ValidationError):
                    self.validator.validate(make_lab(lab_id))


if __name__ == "__main__":
    unittest.main()
