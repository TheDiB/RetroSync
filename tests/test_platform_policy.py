import copy
import itertools
import unittest

from platform_policy import propose_sram, propose_platform
from platform_comparison import compare_platform


A, B, C = (c * 64 for c in "abc")


class PlatformPolicyTests(unittest.TestCase):
    def test_exhaustive_matrix(self):
        # Independent reference table indexed by classification and policy.
        conflicts = {"manual": "BLOCKED", "prefer_local": "PUSH_PROPOSED",
                     "prefer_remote": "PULL_PROPOSED"}
        for local, remote, baseline, conflict, missing in itertools.product(
                (None, A, B, C), (None, A, B, C), (None, A, B, C),
                conflicts, ("block", "create_new", "restore")):
            with self.subTest(local=local, remote=remote, baseline=baseline,
                              conflict=conflict, missing=missing):
                if local is None and remote is None:
                    status, action = "MISSING_BOTH", "BLOCKED"
                elif None in (local, remote):
                    side = "LOCAL" if local is None else "REMOTE"
                    status = "MISSING_" + side
                    action = {
                        "block": "BLOCKED",
                        "create_new": "CREATE_" + side if baseline is None else "CONFIRM_RESTORE",
                        "restore": "CREATE_" + side if baseline is None else "RESTORE_" + side,
                    }[missing]
                elif local == remote:
                    status, action = "IN_SYNC", "NOOP"
                elif baseline is None:
                    status, action = "INITIAL_CONFLICT", conflicts[conflict]
                elif baseline == remote:
                    status, action = "PUSH", "PUSH_PROPOSED"
                elif baseline == local:
                    status, action = "PULL", "PULL_PROPOSED"
                else:
                    status, action = "CONFLICT", conflicts[conflict]
                result = propose_sram(local, remote, baseline,
                                      {"sram": conflict, "missing": missing})
                self.assertEqual((result["classification"], result["action"]), (status, action))
                self.assertFalse(result["write_authorized"])

    def test_default_policy(self):
        self.assertEqual(propose_sram(A, None)["action"], "CREATE_REMOTE")
        self.assertEqual(propose_sram(A, B)["action"], "BLOCKED")

    def test_invalid_inputs(self):
        for args in (("bad", A), (A, B, "bad"), (A, B, None, {"sram": "newest"})):
            with self.subTest(args=args), self.assertRaises(ValueError):
                propose_sram(*args)

    def test_case_normalization(self):
        self.assertEqual(propose_sram(A.upper(), A)["action"], "NOOP")

    def fixture(self):
        def entry(name, digest, kind="SRAM"):
            return {"relative_path": name, "sha256": digest, "kind": kind}
        inventory = {"platform": "gbc", "complete": True, "endpoints": {
            "local": {"files": [entry("Game.srm", B), entry("New.srm", A),
                                entry("Game.state", C, "STATE")]},
            "remote": {"files": [entry("Game.srm", A)]}}}
        item = {"id": "gbc", "inventory": inventory,
                "comparison": compare_platform(inventory), "policy": {}}
        history = {"gbc": {"files": {"Game.srm": {"last_synced_sha256": A},
                                     "Lost.srm": {"last_synced_sha256": B}}}}
        return item, history

    def test_platform_union_and_state_exclusion(self):
        item, history = self.fixture()
        before = copy.deepcopy((item, history))
        result = propose_platform(item, history)
        self.assertEqual([(f["relative_path"], f["action"]) for f in result["files"]],
                         [("Game.srm", "PUSH_PROPOSED"), ("Lost.srm", "BLOCKED"),
                          ("New.srm", "CREATE_REMOTE")])
        self.assertEqual(result["files"][1]["classification"], "MISSING_BOTH")
        self.assertEqual(result["states_excluded"], 1)
        self.assertFalse(result["write_authorized"])
        self.assertFalse(result["attribution_verified"])
        self.assertFalse(result["compatibility_verified"])
        self.assertEqual((item, history), before)

    def test_incomplete_inventory_refused(self):
        item, history = self.fixture()
        item["inventory"]["complete"] = False
        with self.assertRaises(ValueError):
            propose_platform(item, history)

    def test_inconsistent_comparison_refused(self):
        item, history = self.fixture()
        item["comparison"]["files"][0]["local_sha256"] = C
        with self.assertRaisesRegex(ValueError, "mismatch"):
            propose_platform(item, history)

    def test_platform_policy_override(self):
        item, history = self.fixture()
        item["policy"] = {"missing": "block", "sram": "prefer_remote"}
        result = propose_platform(item, history)
        self.assertEqual(result["files"][0]["action"], "PUSH_PROPOSED")
        self.assertEqual(result["files"][2]["action"], "BLOCKED")
