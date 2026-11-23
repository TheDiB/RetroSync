import copy
import json
import tempfile
import unittest
from pathlib import Path

from configuration import load_config, resolve_policy, validate_config


def sample():
    return {"schema_version": 2, "device_id": "deck",
            "nas": {"mount": "/mnt/nas", "expected_source": "//nas/Emulation", "remote_root": "Save"},
            "platforms": [{"id": "gbc",
                           "local": {"emulator": "retroarch", "core": "mgba", "save_dir": "/saves/mGBA"},
                           "remote": {"emulator": "retroarch", "core": "unknown", "save_dir": "gbc"}}]}


class ConfigurationTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(resolve_policy(), {"sram": "manual", "missing": "create_new"})

    def test_policy_inheritance(self):
        self.assertEqual(resolve_policy({"sram": "prefer_remote", "missing": "block"}, {"sram": "prefer_local"}),
                         {"sram": "prefer_local", "missing": "block"})

    def test_invalid_policy(self):
        for policy in ({"sram": "bad"}, {"missing": "delete"}, {"typo": "manual"}, {"sram": []}):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                resolve_policy(policy)

    def test_valid_v2_without_mutation(self):
        config = sample()
        before = copy.deepcopy(config)
        self.assertEqual(validate_config(config), before)
        self.assertEqual(config, before)

    def test_legacy_v1(self):
        config = {"schema_version": 1, "games": []}
        self.assertEqual(validate_config(config), config)

    def test_bad_versions(self):
        for version in (True, 3, "2", None):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_config({"schema_version": version})

    def test_multiple_platforms(self):
        config = sample()
        second = copy.deepcopy(config["platforms"][0])
        second["id"] = "gba"
        second["remote"]["save_dir"] = "gba"
        config["platforms"].append(second)
        validate_config(config)

    def test_duplicate_platform(self):
        config = sample()
        config["platforms"].append(copy.deepcopy(config["platforms"][0]))
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_invalid_remote_paths(self):
        for path in ("../gbc", "/gbc", "a/../gbc", "C:/gbc", "a\\gbc", "a//b", "."):
            config = sample()
            config["platforms"][0]["remote"]["save_dir"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_config(config)

    def test_invalid_local_paths(self):
        for path in ("saves", "/saves/../other", ""):
            config = sample()
            config["platforms"][0]["local"]["save_dir"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_config(config)

    def test_invalid_global_policy(self):
        config = sample()
        config["policy"] = {"missing": "delete"}
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_invalid_platform_policy(self):
        config = sample()
        config["platforms"][0]["policy"] = None
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_invalid_nas_root(self):
        config = sample()
        config["nas"]["remote_root"] = "../Save"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_empty_platforms(self):
        config = sample()
        config["platforms"] = []
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_mixed_schema(self):
        config = sample()
        config["games"] = []
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_load_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps(sample()), encoding="utf-8")
            before = path.read_bytes()
            self.assertEqual(load_config(path), sample())
            self.assertEqual(path.read_bytes(), before)
