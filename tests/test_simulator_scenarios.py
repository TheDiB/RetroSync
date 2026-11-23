import itertools
import json
import unittest
from pathlib import Path

from platform_policy import propose_sram


class SimulatorScenarioTests(unittest.TestCase):
    def test_shared_reference_matrix(self):
        data = json.loads((Path(__file__).resolve().parents[1] /
                           "docs/simulator-scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["columns"], ["local", "remote", "baseline", "sram",
                         "missing", "classification", "action", "write_authorized"])
        expected = set(itertools.product(
            (None, "A", "B", "C"), (None, "A", "B", "C"),
            (None, "A", "B", "C"), ("manual", "prefer_local", "prefer_remote"),
            ("block", "create_new", "restore")))
        self.assertEqual(len(data["cases"]), 576)
        self.assertEqual({tuple(row[:5]) for row in data["cases"]}, expected)
        for local, remote, baseline, sram, missing, status, action, authorized in data["cases"]:
            with self.subTest(local=local, remote=remote, baseline=baseline,
                              sram=sram, missing=missing):
                hashes = [v.lower() * 64 if v is not None else None
                          for v in (local, remote, baseline)]
                result = propose_sram(*hashes, {"sram": sram, "missing": missing})
                self.assertEqual(result["classification"], status)
                self.assertEqual(result["action"], action)
                self.assertIs(authorized, False)
                self.assertIs(result["write_authorized"], False)
