import copy
import json
import tempfile
import unittest
from pathlib import Path

from platform_baseline import (load_platform_baseline, validate_platform_baseline,
                               platform_baseline_hash)
from test_configuration import sample


class PlatformBaselineTests(unittest.TestCase):
    def setUp(self):
        self.config = sample()
        self.name = "Wario Land II (USA, Europe).srm"
        self.data = {"schema_version": 2, "device_id": self.config["device_id"],
                     "platforms": {"gbc": {"files": {self.name: {
                         "last_synced_sha256": "A" * 64,
                         "last_synced_at": "2026-11-23T21:00:00Z"}}}}}

    def test_optional_history(self):
        self.assertEqual(load_platform_baseline(None, self.config), {})

    def test_empty_history(self):
        self.data["platforms"] = {}
        self.assertEqual(validate_platform_baseline(self.data, self.config), {})

    def test_exact_lookup_and_read_only(self):
        before = copy.deepcopy(self.data)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text(json.dumps(self.data), encoding="utf-8")
            raw = path.read_bytes()
            history = load_platform_baseline(path, self.config)
            self.assertEqual(platform_baseline_hash(history, "gbc", self.name), "a" * 64)
            self.assertIsNone(platform_baseline_hash(history, "gbc", self.name.lower()))
            self.assertIsNone(platform_baseline_hash(history, "gba", self.name))
            self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(self.data, before)

    def test_missing_explicit_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                load_platform_baseline(Path(folder) / "missing.json", self.config)

    def test_wrong_device(self):
        self.data["device_id"] = "other"
        with self.assertRaisesRegex(ValueError, "device_id"):
            validate_platform_baseline(self.data, self.config)

    def test_wrong_schema(self):
        for version in (1, True, 2.0, 3):
            with self.subTest(version=version):
                self.data["schema_version"] = version
                with self.assertRaises(ValueError):
                    validate_platform_baseline(self.data, self.config)

    def test_mixed_schema(self):
        self.data["games"] = {}
        with self.assertRaises(ValueError):
            validate_platform_baseline(self.data, self.config)

    def test_unknown_platform(self):
        self.data["platforms"]["unknown"] = {"files": {}}
        with self.assertRaisesRegex(ValueError, "Unknown baseline platform"):
            validate_platform_baseline(self.data, self.config)

    def test_invalid_filenames(self):
        entry = self.data["platforms"]["gbc"]["files"][self.name]
        for name in ("../Game.srm", "/Game.srm", "a\\Game.srm", "C:Game.srm",
                     "Game.state", "Game.state1", ".srm", "a\x00.srm"):
            with self.subTest(name=name):
                self.data["platforms"]["gbc"]["files"] = {name: entry}
                with self.assertRaises(ValueError):
                    validate_platform_baseline(self.data, self.config)

    def test_invalid_hashes(self):
        entry = self.data["platforms"]["gbc"]["files"][self.name]
        for value in (None, "", "g" * 64, "a" * 63, 123):
            with self.subTest(value=value):
                entry["last_synced_sha256"] = value
                with self.assertRaises(ValueError):
                    validate_platform_baseline(self.data, self.config)

    def test_invalid_timestamps(self):
        entry = self.data["platforms"]["gbc"]["files"][self.name]
        for value in (None, "2026-11-23", "2026-02-30T00:00:00Z",
                      "2026-11-23T21:00:00", "2026-11-23T21:00:00+01:00"):
            with self.subTest(value=value):
                entry["last_synced_at"] = value
                with self.assertRaises(ValueError):
                    validate_platform_baseline(self.data, self.config)

    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate baseline key"):
                load_platform_baseline(path, self.config)

    def test_platform_isolation(self):
        second = copy.deepcopy(self.config["platforms"][0])
        second["id"] = "gba"
        self.config["platforms"].append(second)
        self.data["platforms"]["gba"] = copy.deepcopy(self.data["platforms"]["gbc"])
        self.data["platforms"]["gba"]["files"][self.name]["last_synced_sha256"] = "b" * 64
        history = validate_platform_baseline(self.data, self.config)
        self.assertEqual(platform_baseline_hash(history, "gbc", self.name), "a" * 64)
        self.assertEqual(platform_baseline_hash(history, "gba", self.name), "b" * 64)
