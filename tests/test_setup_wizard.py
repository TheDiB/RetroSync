import json
import tempfile
import unittest
from pathlib import Path

from setup_wizard import run_setup


ANSWERS = [
    "steamdeck", "/mnt/nas", "//nas/Emulation", "Save",
    "wario", "Wario Land II", "/home/deck/saves", "gbc",
    "batocera.local", "root",
]


def prompt_from(values):
    iterator = iter(values)
    return lambda _: next(iterator)


class SetupWizardTests(unittest.TestCase):
    def test_dry_run_creates_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "config.json"
            lines = []
            self.assertEqual(run_setup(target, dry_run=True,
                                       ask=prompt_from(ANSWERS), say=lines.append), 0)
            self.assertFalse(target.exists())
            self.assertTrue(any("DRY RUN" in s for s in lines))

    def test_confirm_creates_valid_config(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "config.json"
            self.assertEqual(run_setup(target, ask=prompt_from(ANSWERS + ["yes"]),
                                       say=lambda _: None), 0)
            config = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(config["schema_version"], 1)
            self.assertEqual(config["batocera"]["host"], "batocera.local")
            self.assertEqual(config["games"][0]["remote_dir"], "gbc")

    def test_existing_config_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "config.json"
            target.write_text("original", encoding="utf-8")
            self.assertEqual(run_setup(target, ask=lambda _: self.fail("must not prompt"),
                                       say=lambda _: None), 2)
            self.assertEqual(target.read_text(), "original")

    def test_cancel_does_not_create(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "config.json"
            self.assertEqual(run_setup(target, ask=prompt_from(ANSWERS + ["no"]),
                                       say=lambda _: None), 0)
            self.assertFalse(target.exists())

    def test_invalid_relative_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "config.json"
            bad = ANSWERS.copy()
            bad[7] = "../other"
            with self.assertRaises(ValueError):
                run_setup(target, dry_run=True, ask=prompt_from(bad),
                          say=lambda _: None)
            self.assertFalse(target.exists())

    def test_optional_batocera_can_be_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "config.json"
            self.assertEqual(run_setup(target, ask=prompt_from(ANSWERS[:8] + ["", "yes"]),
                                       say=lambda _: None), 0)
            self.assertNotIn("batocera", json.loads(target.read_text()))

    def test_missing_parent_is_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "missing" / "config.json"
            with self.assertRaises(FileNotFoundError):
                run_setup(target, ask=prompt_from(ANSWERS + ["yes"]),
                          say=lambda _: None)
            self.assertFalse(target.parent.exists())


if __name__ == "__main__":
    unittest.main()
