import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from platform_scan import scan_configured, render_scan
from test_configuration import sample


class PlatformScanTests(unittest.TestCase):
    def test_legacy_refused(self):
        verify = Mock()
        with self.assertRaisesRegex(ValueError, "schema v2"):
            scan_configured({"schema_version": 1}, verify)
        verify.assert_not_called()

    def test_unknown_platform_refused(self):
        verify = Mock()
        with self.assertRaisesRegex(ValueError, "Unknown platform"):
            scan_configured(sample(), verify, "gba")
        verify.assert_not_called()

    def test_overlap_refused_even_with_selection(self):
        config = sample()
        second = copy.deepcopy(config["platforms"][0])
        second["id"] = "gba"
        second["remote"]["save_dir"] = "gba"
        config["platforms"].append(second)
        verify = Mock()
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            scan_configured(config, verify, "gbc")
        verify.assert_not_called()

    def test_mount_failure_before_discovery(self):
        verify = Mock(side_effect=RuntimeError("offline"))
        with patch("platform_scan.discover_platform") as discover:
            with self.assertRaisesRegex(RuntimeError, "offline"):
                scan_configured(sample(), verify)
            discover.assert_not_called()

    def fixture(self, root):
        config = sample()
        mount = root / "nas"
        config["nas"]["mount"] = str(mount)
        for identifier in ("gbc", "gba"):
            local = root / identifier
            remote = mount / "Save" / identifier
            local.mkdir()
            remote.mkdir(parents=True)
            (local / "Game.srm").write_bytes(b"local")
            (remote / "Game.srm").write_bytes(b"remote")
            platform = copy.deepcopy(config["platforms"][0])
            platform["id"] = identifier
            platform["local"]["save_dir"] = str(local)
            platform["remote"]["save_dir"] = identifier
            if identifier == "gbc":
                config["platforms"][0] = platform
            else:
                config["platforms"].append(platform)
        return config

    def test_all_and_selected_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = self.fixture(root)
            before = copy.deepcopy(config)
            verify = Mock()
            # Native temporary paths on Windows are not deployment POSIX paths.
            # Structural validation is exercised separately with real v2 configs.
            with patch("platform_scan.configuration_report",
                       return_value={"schema_version": 2, "warnings": []}):
                report = scan_configured(config, verify)
                selected = scan_configured(config, verify, "gba")
            self.assertEqual([p["id"] for p in report["platforms"]], ["gbc", "gba"])
            self.assertEqual([p["id"] for p in selected["platforms"]], ["gba"])
            self.assertEqual(report["platforms"][0]["comparison"]["counts"]["DIFFERENT"], 1)
            self.assertFalse(report["platforms"][0]["attribution_verified"])
            self.assertFalse(report["sync_decisions"])
            self.assertEqual(config, before)
            self.assertEqual((root / "gbc" / "Game.srm").read_bytes(), b"local")
            self.assertEqual((root / "nas" / "Save" / "gbc" / "Game.srm").read_bytes(), b"remote")
            self.assertIn("inventory only", render_scan(report))

    def test_physical_overlap_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self.fixture(Path(folder))
            config["platforms"][1]["local"]["save_dir"] = config["platforms"][0]["local"]["save_dir"]
            with patch("platform_scan.configuration_report",
                       return_value={"schema_version": 2, "warnings": []}):
                with self.assertRaisesRegex(ValueError, "Overlapping endpoint"):
                    scan_configured(config, Mock())

    def test_mount_loss_after_scan_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            config = self.fixture(Path(folder))
            verify = Mock(side_effect=[None, None, RuntimeError("mount lost")])
            with patch("platform_scan.configuration_report",
                       return_value={"schema_version": 2, "warnings": []}):
                with self.assertRaisesRegex(RuntimeError, "mount lost"):
                    scan_configured(config, verify)

    def alias(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Symlink privilege unavailable")
            raise

    def scan_fixture(self, config):
        with patch("platform_scan.configuration_report",
                   return_value={"schema_version": 2, "warnings": []}):
            return scan_configured(config, Mock())

    def test_local_parent_alias_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = self.fixture(root)
            alias = root / "alias"
            self.alias(alias, root)
            config["platforms"][0]["local"]["save_dir"] = str(alias / "gbc")
            report = self.scan_fixture(config)
            paths = report["platforms"][0]["paths"]["local"]
            self.assertEqual(paths["configured_path"], str(alias / "gbc"))
            self.assertEqual(paths["resolved_path"], str(root / "gbc"))
            self.assertTrue(paths["symlink_resolved"])
            self.assertEqual(report["platforms"][0]["comparison"]["counts"]["DIFFERENT"], 1)
            self.assertIn("local alias:", render_scan(report))

    def test_local_target_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = self.fixture(root)
            self.alias(root / "alias", root / "gbc")
            config["platforms"][0]["local"]["save_dir"] = str(root / "alias")
            with self.assertRaisesRegex(ValueError, "Symlinked endpoint"):
                self.scan_fixture(config)

    def test_remote_parent_alias_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = self.fixture(root)
            self.alias(root / "nas" / "alias", root / "nas" / "Save")
            config["nas"]["remote_root"] = "alias"
            with self.assertRaisesRegex(ValueError, "Symlinked endpoint"):
                self.scan_fixture(config)

    def test_broken_parent_alias_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = self.fixture(root)
            self.alias(root / "alias", root / "missing")
            config["platforms"][0]["local"]["save_dir"] = str(root / "alias" / "gbc")
            with self.assertRaises(OSError):
                self.scan_fixture(config)

    def test_alias_collision_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = self.fixture(root)
            self.alias(root / "alias", root)
            config["platforms"][1]["local"]["save_dir"] = str(root / "alias" / "gbc")
            with self.assertRaisesRegex(ValueError, "Overlapping endpoint"):
                self.scan_fixture(config)

    def test_alias_retarget_during_scan_refused(self):
        from platform_discovery import discover_platform
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = self.fixture(root)
            alias = root / "alias"
            self.alias(alias, root)
            other = root / "other"
            (other / "gbc").mkdir(parents=True)
            config["platforms"][0]["local"]["save_dir"] = str(alias / "gbc")

            def retarget(mapping):
                result = discover_platform(mapping)
                alias.unlink()
                self.alias(alias, other)
                return result

            with patch("platform_scan.discover_platform", side_effect=retarget):
                with self.assertRaisesRegex(RuntimeError, "Endpoint changed"):
                    self.scan_fixture(config)
