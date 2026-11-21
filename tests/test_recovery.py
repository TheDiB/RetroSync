import tempfile
import unittest
from pathlib import Path

from recovery import export_backup_fixture, inspect_fixture
from safe_copy import CopyPreconditionError, sha256


class RecoveryFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.destination = root / "game.srm"
        self.backup = root / "previous.bak"
        self.output = root / "candidate.srm"
        self.destination.write_bytes(b"new progress")
        self.backup.write_bytes(b"old progress")
        self.old_hash = sha256(self.backup)
        self.new_hash = sha256(self.destination)

    def test_audit_verified_files(self):
        report = inspect_fixture(self.destination, self.backup, self.old_hash, self.new_hash)
        self.assertEqual(report["backup_status"], "VERIFIED")
        self.assertEqual(report["destination_status"], "MATCH")
        self.assertTrue(report["can_export_backup"])

    def test_audit_detects_corrupt_backup(self):
        self.backup.write_bytes(b"corrupted")
        report = inspect_fixture(self.destination, self.backup, self.old_hash)
        self.assertEqual(report["backup_status"], "HASH_MISMATCH")
        self.assertFalse(report["can_export_backup"])

    def test_audit_detects_changed_destination(self):
        self.destination.write_bytes(b"unexpected")
        report = inspect_fixture(self.destination, self.backup, self.old_hash, self.new_hash)
        self.assertEqual(report["destination_status"], "HASH_MISMATCH")

    def test_audit_missing_destination(self):
        self.destination.unlink()
        report = inspect_fixture(self.destination, self.backup, self.old_hash)
        self.assertEqual(report["destination_status"], "MISSING")

    def test_audit_missing_backup(self):
        self.backup.unlink()
        report = inspect_fixture(self.destination, self.backup, self.old_hash)
        self.assertEqual(report["backup_status"], "MISSING")
        self.assertFalse(report["can_export_backup"])

    def test_audit_without_destination_hash_does_not_claim_match(self):
        report = inspect_fixture(self.destination, self.backup, self.old_hash)
        self.assertEqual(report["destination_status"], "PRESENT_UNVERIFIED")

    def test_export_creates_new_verified_candidate(self):
        result = export_backup_fixture(self.backup, self.output, self.old_hash)
        self.assertEqual(self.output.read_bytes(), b"old progress")
        self.assertEqual(result["sha256"], self.old_hash)
        self.assertEqual(self.destination.read_bytes(), b"new progress")

    def test_export_refuses_existing_file(self):
        self.output.write_bytes(b"important")
        with self.assertRaises(CopyPreconditionError):
            export_backup_fixture(self.backup, self.output, self.old_hash)
        self.assertEqual(self.output.read_bytes(), b"important")

    def test_export_refuses_corrupt_backup(self):
        self.backup.write_bytes(b"corrupt")
        with self.assertRaises(CopyPreconditionError):
            export_backup_fixture(self.backup, self.output, self.old_hash)
        self.assertFalse(self.output.exists())

    def test_export_refuses_invalid_digest(self):
        with self.assertRaises(CopyPreconditionError):
            export_backup_fixture(self.backup, self.output, "bad")
        self.assertFalse(self.output.exists())

    def test_export_refuses_missing_backup(self):
        self.backup.unlink()
        with self.assertRaises(CopyPreconditionError):
            export_backup_fixture(self.backup, self.output, self.old_hash)

    def test_audit_rejects_invalid_expected_hash(self):
        with self.assertRaises(CopyPreconditionError):
            inspect_fixture(self.destination, self.backup, "bad")


if __name__ == "__main__":
    unittest.main()
