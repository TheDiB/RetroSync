import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from execution_lock import local_execution_lock

CHILD = """
import sys
from execution_lock import local_execution_lock
with local_execution_lock(sys.argv[1]) as result:
    print(result["status"], flush=True)
    if result["status"] == "ACQUIRED":
        sys.stdin.read()
"""


class UnsupportedLockTests(unittest.TestCase):
    def test_unsupported(self):
        with patch("execution_lock.fcntl", None):
            with local_execution_lock("/unused") as result:
                self.assertEqual(result["reason"], "LOCK_UNSUPPORTED")
                self.assertIs(result["write_authorized"], False)


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux flock required")
class LocalLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "retrosync.lock"

    def test_acquire_release(self):
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["status"], "ACQUIRED")
            self.assertIs(result["write_authorized"], False)
            self.assertIs(result["coordination_verified"], False)
        inode = self.path.stat().st_ino
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["status"], "ACQUIRED")
        self.assertEqual(self.path.stat().st_ino, inode)

    def test_contention(self):
        with local_execution_lock(self.root):
            with local_execution_lock(self.root) as result:
                self.assertEqual(result["reason"], "LOCK_BUSY")

    def test_exception_release(self):
        with self.assertRaisesRegex(RuntimeError, "body"):
            with local_execution_lock(self.root):
                raise RuntimeError("body")
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["status"], "ACQUIRED")

    def test_process_contention_and_kill(self):
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", CHILD, str(self.root)],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True)
        try:
            import select
            ready, _, _ = select.select([child.stdout], [], [], 10)
            self.assertTrue(ready, "Child did not report lock status")
            self.assertEqual(child.stdout.readline().strip(), "ACQUIRED")
            with local_execution_lock(self.root) as result:
                self.assertEqual(result["reason"], "LOCK_BUSY")
            child.kill()
            child.communicate(timeout=10)
            self.assertLess(child.returncode, 0)
            with local_execution_lock(self.root) as result:
                self.assertEqual(result["status"], "ACQUIRED")
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_symlink(self):
        target = self.root / "target"
        target.write_text("unchanged")
        self.path.symlink_to(target)
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["reason"], "LOCK_UNAVAILABLE")
        self.assertEqual(target.read_text(), "unchanged")

    def test_fifo(self):
        os.mkfifo(self.path, 0o600)
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["reason"], "LOCK_UNAVAILABLE")

    def test_public_directory(self):
        self.root.chmod(0o755)
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["reason"], "LOCK_UNAVAILABLE")
        self.assertFalse(self.path.exists())

    def test_public_file(self):
        self.path.touch()
        self.path.chmod(0o644)
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["reason"], "LOCK_UNAVAILABLE")

    def test_hardlink(self):
        target = self.root / "target"
        target.touch(mode=0o600)
        os.link(target, self.path)
        with local_execution_lock(self.root) as result:
            self.assertEqual(result["reason"], "LOCK_UNAVAILABLE")

    def test_missing_directory(self):
        with local_execution_lock(self.root / "missing") as result:
            self.assertEqual(result["reason"], "LOCK_UNAVAILABLE")
