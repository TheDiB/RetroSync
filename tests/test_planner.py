import unittest

from planner import plan_sram


def h(char):
    return char * 64


class PlannerTests(unittest.TestCase):
    def plan(self, local, remote, baseline=None):
        return plan_sram("/deck/game.srm", "/nas/game.srm",
                         local, remote, baseline)

    def test_pull_proposes_copy_with_preconditions(self):
        plan = self.plan(h("a"), h("b"), h("a"))
        self.assertEqual(plan["decision"], "PULL")
        self.assertEqual(plan["operation"], "COPY_PROPOSED")
        self.assertEqual(plan["source"], "/nas/game.srm")
        self.assertEqual(plan["destination"], "/deck/game.srm")
        self.assertEqual(plan["expected_source_sha256"], h("b"))
        self.assertEqual(plan["expected_destination_sha256"], h("a"))
        self.assertTrue(plan["read_only"])

    def test_push_proposes_reverse_copy(self):
        plan = self.plan(h("b"), h("a"), h("a"))
        self.assertEqual(plan["decision"], "PUSH")
        self.assertEqual(plan["source"], "/deck/game.srm")
        self.assertEqual(plan["destination"], "/nas/game.srm")

    def test_in_sync_is_noop(self):
        plan = self.plan(h("b"), h("b"))
        self.assertEqual(plan["operation"], "NONE")
        self.assertIsNone(plan["source"])

    def test_initial_conflict_blocks(self):
        plan = self.plan(h("a"), h("b"))
        self.assertEqual(plan["operation"], "BLOCKED")
        self.assertTrue(plan["requires_review"])

    def test_conflict_blocks(self):
        self.assertEqual(self.plan(h("b"), h("c"), h("a"))["operation"], "BLOCKED")

    def test_missing_local_blocks(self):
        self.assertEqual(self.plan(None, h("a"), h("a"))["operation"], "BLOCKED")

    def test_missing_remote_blocks(self):
        self.assertEqual(self.plan(h("a"), None, h("a"))["operation"], "BLOCKED")

    def test_missing_both_blocks(self):
        self.assertEqual(self.plan(None, None)["operation"], "BLOCKED")

    def test_invalid_hash_fails_closed(self):
        with self.assertRaises(ValueError):
            self.plan("bad", h("a"))

    def test_same_paths_rejected_for_copy(self):
        with self.assertRaises(ValueError):
            plan_sram("/same", "/same", h("a"), h("b"), h("a"))

    def test_wario_historical_pull(self):
        old = "91f6e75149f3f6477a9cdc72fd1d2879ddf3a24dc265a6687136f9303661018a"
        nas = "14a77e2aa76063a636fd5f65223751baf086e11154e5317b49442ba74e66fa6b"
        plan = self.plan(old, nas, old)
        self.assertEqual(plan["decision"], "PULL")
        self.assertEqual(plan["operation"], "COPY_PROPOSED")
        self.assertEqual(plan["expected_source_sha256"], nas)


if __name__ == "__main__":
    unittest.main()
