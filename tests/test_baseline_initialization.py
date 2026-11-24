import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from baseline_initialization import (build_baseline_draft, mapping_fingerprint,
    validate_baseline_draft, persist_baseline_fixture)
from platform_baseline import load_platform_baseline
from test_configuration import sample


class BaselineInitializationTests(unittest.TestCase):
    def setUp(self):
        self.config = sample()
        self.comparison = {"platform": "gbc", "files": [
            {"kind": "SRAM", "status": "IDENTICAL", "relative_path": "Same.srm",
             "local_sha256": "a" * 64},
            {"kind": "SRAM", "status": "DIFFERENT", "relative_path": "Conflict.srm"},
            {"kind": "SRAM", "status": "LOCAL_ONLY", "relative_path": "Local.srm"},
            {"kind": "SRAM", "status": "REMOTE_ONLY", "relative_path": "Remote.srm"},
            {"kind": "STATE", "status": "IDENTICAL", "relative_path": "Same.state"}]}
        self.scan = {"complete": True, "device_id": self.config["device_id"],
                     "platforms": [{"id": "gbc", "inventory": {},
                                    "comparison": self.comparison}]}

    def draft(self):
        with patch("baseline_initialization.scan_configured", return_value=self.scan), \
             patch("baseline_initialization.compare_platform", return_value=self.comparison):
            return build_baseline_draft(self.config, lambda *args: None)

    def test_only_identical_sram(self):
        data = self.draft()
        self.assertEqual(set(data["platforms"]["gbc"]["files"]), {"Same.srm"})
        self.assertIs(data["initialization"]["provenance_verified"], False)
        self.assertEqual(data["platforms"]["gbc"]["files"]["Same.srm"]["last_synced_sha256"], "a" * 64)

    def test_incomplete_scan(self):
        self.scan["complete"] = False
        with self.assertRaises(ValueError):
            self.draft()

    def test_missing_platform(self):
        self.scan["platforms"] = []
        with self.assertRaises(ValueError):
            self.draft()

    def test_mapping_change(self):
        data = self.draft()
        self.config["platforms"][0]["remote"]["core"] = "other"
        with self.assertRaises(ValueError):
            validate_baseline_draft(data, self.config)

    def test_policy_change_does_not_change_mapping(self):
        before = mapping_fingerprint(self.config)
        self.config["policy"] = {"sram": "prefer_remote"}
        self.assertEqual(mapping_fingerprint(self.config), before)

    def test_no_mutation(self):
        before = copy.deepcopy(self.config)
        self.draft()
        self.assertEqual(self.config, before)

    def test_forged_provenance(self):
        data = self.draft()
        data["initialization"]["provenance_verified"] = True
        with self.assertRaises(ValueError):
            validate_baseline_draft(data, self.config)

    def test_exclusive_persistence(self):
        data = self.draft()
        with tempfile.TemporaryDirectory() as folder:
            path = persist_baseline_fixture(data, self.config, folder)
            raw = path.read_bytes()
            self.assertEqual(load_platform_baseline(path, self.config), data["platforms"])
            with self.assertRaises(FileExistsError):
                persist_baseline_fixture(data, self.config, folder)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_publish_failure_leaves_no_final_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("baseline_initialization.os.link", side_effect=OSError("unsupported")):
                with self.assertRaises(OSError):
                    persist_baseline_fixture(self.draft(), self.config, folder)
            self.assertEqual(list(Path(folder).iterdir()), [])
