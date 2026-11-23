import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from platform_plan import build_plan, render_plan
from test_configuration import sample
import test_platform_policy
import retro_sync


class PlatformPlanTests(unittest.TestCase):
    def fixture(self):
        item, _ = test_platform_policy.PlatformPolicyTests().fixture()
        item["paths"] = {side: {"configured_path": "/" + side,
                               "resolved_path": "/" + side,
                               "symlink_resolved": False}
                         for side in ("local", "remote")}
        return {"device_id": sample()["device_id"], "platforms": [item]}

    def test_plan_without_history(self):
        with patch("platform_plan.scan_configured", return_value=self.fixture()):
            report = build_plan(sample(), Mock())
        self.assertEqual(report["counts"], {"BLOCKED": 1, "CREATE_REMOTE": 1})
        self.assertEqual(report["sram_total"], 2)
        self.assertEqual(report["states_excluded"], 1)
        self.assertFalse(report["write_authorized"])
        self.assertIn("Authorized writes: 0", render_plan(report))
        self.assertIn("INITIAL_CONFLICT", render_plan(report))

    def test_explicit_missing_baseline_before_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("platform_plan.scan_configured") as scan:
                with self.assertRaises(FileNotFoundError):
                    build_plan(sample(), Mock(), baseline_path=Path(folder) / "missing.json")
                scan.assert_not_called()

    def test_invalid_baseline_before_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text("{}", encoding="utf-8")
            with patch("platform_plan.scan_configured") as scan:
                with self.assertRaises(ValueError):
                    build_plan(sample(), Mock(), baseline_path=path)
                scan.assert_not_called()

    def test_selection_forwarded(self):
        config, verify = sample(), Mock()
        with patch("platform_plan.scan_configured", return_value=self.fixture()) as scan:
            build_plan(config, verify, "gbc")
        scan.assert_called_once_with(config, verify, "gbc")

    def test_legacy_refused(self):
        with patch("platform_plan.scan_configured") as scan:
            with self.assertRaises(ValueError):
                build_plan({"schema_version": 1}, Mock())
            scan.assert_not_called()

    def test_cli_json_dispatch(self):
        with patch("sys.argv", ["retro_sync.py", "--plan", "--platform", "gbc", "--json"]), \
             patch("retro_sync.load_config", return_value=sample()), \
             patch("retro_sync.build_plan", return_value={"read_only": True}) as plan, \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(retro_sync.main(), 0)
        self.assertEqual(json.loads(out.getvalue()), {"read_only": True})
        plan.assert_called_once_with(sample(), retro_sync.check_mount, "gbc", None)

    def test_conflicting_modes(self):
        for flag in ("--scan", "--setup", "--check", "--validate-config", "--platform-preview", "--dry-run"):
            with self.subTest(flag=flag), patch("sys.argv", ["retro_sync.py", "--plan", flag]), \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                retro_sync.main()
            self.assertEqual(exc.exception.code, 2)
