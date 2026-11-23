import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from configuration import configuration_report
from test_configuration import sample

SCRIPT = Path(__file__).resolve().parents[1] / "retro_sync.py"


class ConfigurationCliTests(unittest.TestCase):
    def run_cli(self, config, *args):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "--config", str(path), *args],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(path.read_bytes(), before)
            return result

    def test_offline_json(self):
        config = sample()
        config["policy"] = {"sram": "prefer_remote"}
        result = self.run_cli(config, "--validate-config", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "VALID")
        self.assertEqual(report["platforms"][0]["policy"],
                         {"sram": "prefer_remote", "missing": "create_new"})

    def test_human_report(self):
        result = self.run_cli(sample(), "--validate-config")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Configuration: VALID", result.stdout)
        self.assertIn("No filesystem scan performed.", result.stdout)

    def test_legacy_recognized_not_validated(self):
        result = self.run_cli({"schema_version": 1}, "--validate-config", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "LEGACY_SCHEMA_RECOGNIZED")

    def test_invalid_v2(self):
        config = sample()
        config["platforms"] = []
        result = self.run_cli(config, "--validate-config")
        self.assertEqual(result.returncode, 2)

    def test_unimplemented_v2_modes_refused(self):
        for args in ((), ("--check",), ("--platform-preview",)):
            with self.subTest(args=args):
                result = self.run_cli(sample(), *args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("supports --validate-config, --scan and --plan only", result.stderr)

    def test_conflicting_modes_refused(self):
        result = self.run_cli(sample(), "--validate-config", "--setup")
        self.assertEqual(result.returncode, 2)

    def test_overlap_warning(self):
        config = sample()
        import copy
        second = copy.deepcopy(config["platforms"][0])
        second["id"] = "gba"
        second["remote"]["save_dir"] = "gba"
        config["platforms"].append(second)
        report = configuration_report(config)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("Overlapping local directories", report["warnings"][0])

    def test_nested_overlap_warning(self):
        config = sample()
        import copy
        second = copy.deepcopy(config["platforms"][0])
        second["id"] = "gba"
        second["local"]["save_dir"] = "/saves/mGBA/gba"
        second["remote"]["save_dir"] = "gba"
        config["platforms"].append(second)
        self.assertEqual(len(configuration_report(config)["warnings"]), 1)
