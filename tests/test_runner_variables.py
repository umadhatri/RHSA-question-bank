from __future__ import annotations

import unittest

from grader.runner import generate_variables


class RunnerVariableTests(unittest.TestCase):
    def test_seed_reproduces_all_random_types(self):
        specs = {
            "TOKEN": {"type": "random_token"},
            "IP": {"type": "random_ipv4", "min": 20, "max": 30},
            "COUNT": {"type": "random_int", "min": 7, "max": 9},
            "USER": {"type": "random_username"},
            "GROUP": {"type": "random_group"},
        }
        self.assertEqual(generate_variables(specs, 12345), generate_variables(specs, 12345))

    def test_random_ipv4_and_int_respect_ranges(self):
        values = generate_variables(
            {
                "IP": {"type": "random_ipv4", "min": 80, "max": 90},
                "COUNT": {"type": "random_int", "min": 4, "max": 6},
            },
            42,
        )
        host = int(values["IP"].rsplit(".", 1)[1])
        self.assertTrue(80 <= host <= 90)
        self.assertTrue(4 <= int(values["COUNT"]) <= 6)


if __name__ == "__main__":
    unittest.main()
