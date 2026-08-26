from __future__ import annotations

import unittest
from unittest.mock import patch

from grader.runner import ensure_image


class RunnerImageOverrideTests(unittest.TestCase):
    @patch("grader.runner.image_exists", return_value=True)
    def test_image_override_takes_precedence_over_lab_image(self, _image_exists):
        lab = {"environment": {"image": "cyberrange/rhsa-base:0.3"}}
        override = (
            "766363046973.dkr.ecr.ap-south-1.amazonaws.com/"
            "cyberrange/rhsa-base:0.3"
        )
        self.assertEqual(ensure_image(lab, False, override), override)


if __name__ == "__main__":
    unittest.main()
