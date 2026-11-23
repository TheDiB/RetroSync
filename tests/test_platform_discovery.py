import tempfile
import unittest
from pathlib import Path

from platform_discovery import classify_save, discover_platform, scan_directory


class ClassificationTests(unittest.TestCase):
    def test_sram_and_states(self):
        self.assertEqual(classify_save("Wario.srm"), ("SRAM", None))
        self.assertEqual(classify_save("Wario.state"), ("STATE", 0))
        self.assertEqual(classify_save("Wario.state12"), ("STATE", 12))
        self.assertEqual(classify_save("Wario.STATE2"), ("STATE", 2))
        for name in ("Wario.stateX", "Wario.srm.bak", ".srm", "notes.txt"):
            with self.subTest(name=name):
                self.assertIsNone(classify_save(name))


class DiscoveryTests(unittest.TestCase):
    def test_two_sides_keep_core_identity_and_states(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            local, remote = root / "local", root / "remote"
            local.mkdir()
            remote.mkdir()
            (local / "Wario.srm").write_bytes(b"local")
            (local / "Wario.state1").write_bytes(b"state")
            (remote / "Wario.srm").write_bytes(b"remote")
            (remote / "Other.state").write_bytes(b"other")
            mapping = {"id": "gbc",
                       "local": {"emulator": "retroarch", "core": "mgba", "save_dir": str(local)},
                       "remote": {"emulator": "retroarch", "core": "unknown", "save_dir": str(remote)}}
            result = discover_platform(mapping)
            self.assertTrue(result["complete"])
            self.assertEqual(result["endpoints"]["local"]["core"], "mgba")
            self.assertEqual(result["endpoints"]["remote"]["core"], "unknown")
            self.assertEqual([f["kind"] for f in result["endpoints"]["local"]["files"]],
                             ["SRAM", "STATE"])
            self.assertNotEqual(result["endpoints"]["local"]["files"][0]["sha256"],
                                result["endpoints"]["remote"]["files"][1]["sha256"])

    def test_large_flat_library(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i in range(300):
                (root / f"Game{i:04d}.state2").write_bytes(b"test")
            files = scan_directory(root)
            self.assertEqual(len(files), 300)
            self.assertTrue(all(f["slot"] == 2 for f in files))

    def test_scan_limit_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                (Path(d) / f"game{i}.srm").write_bytes(b"x")
            with self.assertRaisesRegex(RuntimeError, "limit"):
                scan_directory(d, max_entries=2)

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "save.srm").write_bytes(b"safe")
            (root / "alias.srm").symlink_to(root / "save.srm")
            with self.assertRaisesRegex(RuntimeError, "Symlink"):
                scan_directory(root)

    def test_nested_directory_requires_explicit_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "nested").mkdir()
            with self.assertRaisesRegex(RuntimeError, "Subdirectory"):
                scan_directory(d)

    def test_unknown_extensions_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "game.png").write_bytes(b"image")
            self.assertEqual(scan_directory(d), [])

    def test_missing_directory_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                scan_directory(Path(d) / "missing")

    def test_invalid_mapping_fails(self):
        with self.assertRaises(ValueError):
            discover_platform({"id": "gbc", "local": {}, "remote": {}})


if __name__ == "__main__":
    unittest.main()
