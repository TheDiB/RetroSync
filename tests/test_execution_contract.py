import itertools
import unittest

from execution_contract import assess_candidate
from platform_policy import propose_sram


class ExecutionContractTests(unittest.TestCase):
    def proposal(self, local="a" * 64, remote="b" * 64, baseline=None, policy=None):
        return {"relative_path": "Game.srm",
                **propose_sram(local, remote, baseline, policy)}

    def test_matrix_never_authorizes(self):
        hashes = [None, "a" * 64, "b" * 64, "c" * 64]
        for local, remote, baseline, sram, missing in itertools.product(
                hashes, hashes, hashes, ("manual", "prefer_local", "prefer_remote"),
                ("block", "create_new", "restore")):
            with self.subTest(local=local, remote=remote, baseline=baseline,
                              sram=sram, missing=missing):
                p = self.proposal(local, remote, baseline,
                                  {"sram": sram, "missing": missing})
                r = assess_candidate(p)
                self.assertIs(r["write_authorized"], False)
                self.assertEqual(r["status"], "NOOP" if p["action"] == "NOOP" else "BLOCKED")
                c = r["candidate"]
                if p["action"] in ("NOOP", "BLOCKED", "CONFIRM_RESTORE"):
                    self.assertIsNone(c)
                else:
                    self.assertIsNotNone(c["expected_source_sha256"])
                    self.assertNotEqual(c["source_side"], c["destination_side"])
                    self.assertEqual(c["expected_source_sha256"], p[c["source_side"] + "_sha256"])
                    self.assertEqual(c["expected_destination_sha256"], p[c["destination_side"] + "_sha256"])
                    if c["operation"] == "REPLACE":
                        self.assertIsNotNone(c["expected_destination_sha256"])
                        self.assertNotEqual(c["expected_source_sha256"], c["expected_destination_sha256"])
                    else:
                        self.assertIsNone(c["expected_destination_sha256"])

    def test_directions(self):
        a, b = "a" * 64, "b" * 64
        for local, remote, baseline, policy, operation, source in [
            (a, None, None, {}, "CREATE", "local"),
            (None, a, None, {}, "CREATE", "remote"),
            (a, None, b, {"missing": "restore"}, "RESTORE", "local"),
            (None, a, b, {"missing": "restore"}, "RESTORE", "remote"),
            (a, b, b, {}, "REPLACE", "local"),
            (a, b, a, {}, "REPLACE", "remote"),
        ]:
            with self.subTest(operation=operation, source=source):
                c = assess_candidate(self.proposal(local, remote, baseline, policy))["candidate"]
                self.assertEqual((c["operation"], c["source_side"]), (operation, source))

    def test_forged_proposal_rejected(self):
        for key, value in [("write_authorized", True), ("write_authorized", 0),
                           ("action", "PUSH_PROPOSED"), ("classification", "PUSH"),
                           ("local_sha256", "invalid"), ("policy", {})]:
            with self.subTest(key=key, value=value):
                p = self.proposal()
                p[key] = value
                with self.assertRaises(ValueError):
                    assess_candidate(p)

    def test_invalid_filename(self):
        for name in ("../Game.srm", "Game.state", "a/b.srm", "C:Game.srm", None):
            with self.subTest(name=name):
                p = self.proposal()
                p["relative_path"] = name
                with self.assertRaises(ValueError):
                    assess_candidate(p)

    def test_missing_fields(self):
        for key in self.proposal():
            p = self.proposal()
            del p[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                assess_candidate(p)

    def test_confirmation_required(self):
        r = assess_candidate(self.proposal(None, "a" * 64, "b" * 64))
        self.assertEqual(r["reason"], "RESTORE_CONFIRMATION_REQUIRED")
        self.assertIsNone(r["candidate"])
