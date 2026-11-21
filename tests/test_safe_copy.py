import tempfile
import unittest
from pathlib import Path

from safe_copy import CopyPreconditionError, copy_fixture, sha256


class SafeCopyFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.srm"
        self.destination = self.root / "destination.srm"
        self.backups = self.root / "backups"
        self.backups.mkdir()
        self.source.write_bytes(b"new progress")
        self.destination.write_bytes(b"old progress")
        self.old_hash = sha256(self.destination)
        self.new_hash = sha256(self.source)

    def execute(self, source_hash=None, dest_hash=None):
        return copy_fixture(self.source, self.destination, self.backups,
                            source_hash or self.new_hash, dest_hash or self.old_hash)

    def test_copy_creates_verified_backup(self):
        result = self.execute()
        self.assertEqual(self.destination.read_bytes(), b"new progress")
        self.assertEqual(Path(result["backup"]).read_bytes(), b"old progress")
        self.assertEqual(result["sha256"], self.new_hash)
        self.assertEqual(list(self.root.glob(".retrosync-stage-*")), [])

    def test_stale_source_blocks_without_destination_change(self):
        self.source.write_bytes(b"changed")
        with self.assertRaises(CopyPreconditionError):
            self.execute()
        self.assertEqual(self.destination.read_bytes(), b"old progress")

    def test_stale_destination_blocks_without_overwrite(self):
        self.destination.write_bytes(b"newer progress")
        with self.assertRaises(CopyPreconditionError):
            self.execute()
        self.assertEqual(self.destination.read_bytes(), b"newer progress")

    def test_missing_destination_blocks(self):
        self.destination.unlink()
        with self.assertRaises(CopyPreconditionError):
            self.execute()

    def test_invalid_hash_blocks(self):
        with self.assertRaises(CopyPreconditionError):
            self.execute(source_hash="not-a-hash")
        self.assertEqual(self.destination.read_bytes(), b"old progress")

    def test_identical_paths_block(self):
        with self.assertRaises(CopyPreconditionError):
            copy_fixture(self.source, self.source, self.backups,
                         self.new_hash, self.new_hash)

    def test_symlink_destination_blocks(self):
        self.destination.unlink()
        try:
            self.destination.symlink_to(self.source)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable in this environment: {exc}")
        with self.assertRaises(CopyPreconditionError):
            self.execute()

    def test_missing_backup_directory_blocks(self):
        self.backups.rmdir()
        with self.assertRaises(CopyPreconditionError):
            self.execute()


if __name__ == "__main__":
    unittest.main()
