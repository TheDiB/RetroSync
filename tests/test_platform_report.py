import unittest

from platform_comparison import compare_platform
from platform_report import render_platform_report


def file(name, digest, kind="SRAM", slot=None):
    return {"relative_path": name, "sha256": digest * 64, "kind": kind, "slot": slot}


def inventory(local, remote, local_core="mgba", remote_core="unknown"):
    return {"platform": "gbc", "complete": True, "endpoints": {
        "local": {"core": local_core, "files": local},
        "remote": {"core": remote_core, "files": remote},
    }}


class HumanReportTests(unittest.TestCase):
    def test_status_counts_and_sram_warnings(self):
        data = inventory(
            [file("same.srm", "a"), file("diff.srm", "a"),
             file("local.srm", "a"), file("state.state2", "a", "STATE", 2)],
            [file("same.srm", "a"), file("diff.srm", "b"),
             file("remote.srm", "b"), file("state.state2", "b", "STATE", 2)])
        text = render_platform_report(data, compare_platform(data))
        self.assertIn("IDENTICAL", text)
        self.assertIn("DIFFERENT", text)
        self.assertIn("LOCAL_ONLY: local.srm", text)
        self.assertIn("REMOTE_ONLY: remote.srm", text)
        self.assertIn("Divergent SRAM", text)
        self.assertIn("diff.srm", text)
        self.assertIn("core is unknown", text)
        self.assertIn("inventory only", text)
        self.assertIn("No master/slave policy applied", text)

    def test_duplicate_content_different_names(self):
        data = inventory([file("a.srm", "a"), file("b.srm", "a")], [])
        text = render_platform_report(data, compare_platform(data))
        self.assertIn("local: a.srm | b.srm", text)

    def test_known_different_cores_warn(self):
        data = inventory([], [], remote_core="gambatte")
        self.assertIn("cores differ", render_platform_report(data, compare_platform(data)))

    def test_empty_inventory(self):
        data = inventory([], [], remote_core="mgba")
        text = render_platform_report(data, compare_platform(data))
        self.assertIn("(none)", text)
        self.assertIn("Same declared core does not prove", text)

    def test_incomplete_inventory_rejected(self):
        data = inventory([], [])
        data["complete"] = False
        with self.assertRaises(ValueError):
            render_platform_report(data, compare_platform(inventory([], [])))

    def test_mismatched_counts_rejected(self):
        data = inventory([file("a.srm", "a")], [])
        result = compare_platform(data)
        result["counts"]["LOCAL_ONLY"] = 2
        with self.assertRaisesRegex(ValueError, "totals"):
            render_platform_report(data, result)


if __name__ == "__main__":
    unittest.main()
