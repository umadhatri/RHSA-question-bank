from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repo.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location(
        "catalog_registry_validator_test",
        VALIDATOR,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CatalogRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_validator_module()
        cls.catalogs = cls.module.load_catalogs()

    def test_two_product_catalogs_are_registered(self):
        ids = [catalog.marketplace_lab_id for catalog in self.catalogs]
        self.assertEqual(
            ids,
            ["linux-sysadmin-lab", "linux-security-workshop"],
        )

    def test_linux_catalog_owns_only_tupe_and_rhsa_prefixes(self):
        linux = next(
            c for c in self.catalogs
            if c.marketplace_lab_id == "linux-sysadmin-lab"
        )
        self.assertEqual(linux.prefixes, ("TUPE-", "RHSA-"))




    def test_every_current_lab_has_exactly_one_catalog_owner(self):
        locations = self.module.discover_lab_id_locations(ROOT / "labs")
        for lab_id in locations:
            with self.subTest(lab_id=lab_id):
                owner = self.module._catalog_for_lab_id(
                    lab_id,
                    self.catalogs,
                )
                self.assertIsNotNone(owner)


if __name__ == "__main__":
    unittest.main()
