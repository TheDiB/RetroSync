import copy
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from platform_preflight import preflight_v2
from test_configuration import sample


class PlatformPreflightTests(unittest.TestCase):
    def setUp(self):
        self.config = sample()
        self.config["batocera"] = {"host": "batocera"}
        self.mount = Mock()
        self.local = Mock(return_value=("STOPPED", "idle"))
        self.remote = Mock(return_value=("STOPPED", "idle"))

    def run_check(self):
        with patch("platform_preflight._resolve_endpoint",
                   side_effect=lambda path, side: (Path("/fixture") / side, (1, 1 if side == "local" else 2))), \
             patch("platform_preflight._verify_endpoints"), \
             patch.object(Path, "samefile", return_value=False):
            return preflight_v2(self.config, self.mount,
                                local_detector=self.local, remote_detector=self.remote)

    def test_ready_never_authorizes(self):
        before = copy.deepcopy(self.config)
        result = self.run_check()
        self.assertEqual(result["status"], "READY")
        self.assertIs(result["read_only"], True)
        for key in ("write_authorized", "coordination_verified", "attribution_verified",
                    "compatibility_verified", "baseline_provenance_verified"):
            self.assertIs(result[key], False)
        self.assertEqual(self.config, before)
        self.assertEqual(self.mount.call_count, 2)
        self.remote.assert_called_once_with("batocera", user="root")

    def test_invalid_config(self):
        self.config["schema_version"] = 1
        self.assertEqual(self.run_check()["status"], "BLOCKED")
        self.mount.assert_not_called()

    def test_invalid_ssh(self):
        self.config["batocera"]["host"] = "-option"
        self.assertEqual(self.run_check()["status"], "BLOCKED")
        self.mount.assert_not_called()

    def test_unsupported_emulator(self):
        self.config["platforms"][0]["local"]["emulator"] = "other"
        self.assertEqual(self.run_check()["status"], "BLOCKED")
        self.mount.assert_not_called()

    def test_mount_failure(self):
        self.mount.side_effect = subprocess.TimeoutExpired("findmnt", 5)
        self.assertEqual(self.run_check()["status"], "DEFERRED")
        self.local.assert_not_called()
        self.remote.assert_not_called()

    def test_mount_loss(self):
        self.mount.side_effect = [None, RuntimeError("lost")]
        self.assertEqual(self.run_check()["status"], "DEFERRED")

    def test_local_activity(self):
        for status in ("RUNNING", "UNKNOWN", "unexpected"):
            with self.subTest(status=status):
                self.local.return_value = (status, "detail")
                self.assertEqual(self.run_check()["status"], "DEFERRED")

    def test_remote_activity(self):
        for status in ("RUNNING", "UNKNOWN", "unexpected"):
            with self.subTest(status=status):
                self.remote.return_value = (status, "detail")
                self.assertEqual(self.run_check()["status"], "DEFERRED")

    def test_missing_remote(self):
        del self.config["batocera"]
        self.assertEqual(self.run_check()["status"], "DEFERRED")
        self.remote.assert_not_called()

    def test_detector_exception(self):
        self.remote.side_effect = RuntimeError("offline")
        self.assertEqual(self.run_check()["status"], "DEFERRED")

    def test_unsafe_endpoint(self):
        with patch("platform_preflight._resolve_endpoint", side_effect=ValueError("alias")):
            result = preflight_v2(self.config, self.mount, local_detector=self.local,
                                  remote_detector=self.remote)
        self.assertEqual(result["status"], "BLOCKED")
        self.local.assert_not_called()

    def test_physical_overlap(self):
        with patch("platform_preflight._resolve_endpoint", return_value=(Path("/same"), (1, 2))):
            result = preflight_v2(self.config, self.mount, local_detector=self.local,
                                  remote_detector=self.remote)
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_endpoint(self):
        with patch("platform_preflight._resolve_endpoint", side_effect=FileNotFoundError()):
            result = preflight_v2(self.config, self.mount, local_detector=self.local,
                                  remote_detector=self.remote)
        self.assertEqual(result["status"], "DEFERRED")

    def test_endpoint_recheck_failure(self):
        with patch("platform_preflight._resolve_endpoint",
                   side_effect=lambda path, side: (Path("/fixture") / side, (1, 2))), \
             patch.object(Path, "samefile", return_value=False), \
             patch("platform_preflight._verify_endpoints", side_effect=RuntimeError("changed")):
            result = preflight_v2(self.config, self.mount, local_detector=self.local,
                                  remote_detector=self.remote)
        self.assertEqual(result["status"], "DEFERRED")
