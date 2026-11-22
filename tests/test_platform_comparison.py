import unittest

from platform_comparison import compare_platform


def item(name, kind="SRAM", sha="a", slot=None):
    return {"relative_path": name, "kind": kind, "sha256": sha * 64, "slot": slot}


def report(local, remote, complete=True):
    return {"platform": "gbc", "complete": complete, "endpoints": {
        "local": {"files": local}, "remote": {"files": remote}}}


class PlatformComparisonTests(unittest.TestCase):
    def test_all_four_statuses_and_separate_states(self):
        result = compare_platform(report(
            [item("same.srm"), item("different.srm"), item("onlylocal.srm"),
             item("Wario.state2", "STATE", "a", 2)],
            [item("same.srm"), item("different.srm", sha="b"),
             item("onlyremote.srm"), item("Wario.state2", "STATE", "b", 2)]))
        self.assertEqual(result["counts"], {
            "IDENTICAL": 1, "DIFFERENT": 2, "LOCAL_ONLY": 1, "REMOTE_ONLY": 1})
        self.assertEqual(result["files"][-1]["kind"], "STATE")
        self.assertFalse(result["sync_decisions"])

    def test_different_timestamp_does_not_affect_identity(self):
        left = item("a.srm")
        right = item("a.srm")
        left["mtime_ns"] = 100
        right["mtime_ns"] = 200
        self.assertEqual(compare_platform(report([left], [right]))["counts"]["IDENTICAL"], 1)

    def test_empty_platform(self):
        self.assertEqual(compare_platform(report([], []))["files"], [])

    def test_incomplete_report_rejected(self):
        with self.assertRaises(ValueError):
            compare_platform(report([], [], complete=False))

    def test_duplicate_file_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compare_platform(report([item("a.srm"), item("a.srm")], []))

    def test_invalid_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            compare_platform(report([item("a.srm", sha="z")], []))

    def test_kind_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "Inconsistent"):
            compare_platform(report([item("a.srm")], [item("a.srm", "STATE", slot=0)]))

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            compare_platform(report([item("../a.srm")], []))


if __name__ == "__main__":
    unittest.main()
