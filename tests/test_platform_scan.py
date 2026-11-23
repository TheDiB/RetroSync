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
