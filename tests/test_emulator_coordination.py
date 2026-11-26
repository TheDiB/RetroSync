import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from emulator_coordination import fixture_admission

CHILD = """
import json
import sys
from emulator_coordination import fixture_admission
with fixture_admission(sys.argv[1], sys.argv[2],
                       detector=lambda: ("STOPPED", "")) as report:
    print(json.dumps(report), flush=True)
    if report["status"] == "ADMITTED":
        sys.stdin.read()
"""


class AdmissionPortableTests(unittest.TestCase):
    def test_invalid_role(self):
        detector = Mock()
        with fixture_admission("/unused", "invalid", detector=detector) as report:
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["reason"], "INVALID_ROLE")
        detector.assert_not_called()

    def test_unsupported_lock(self):
        detector = Mock()
        with patch("execution_lock.fcntl", None):
            with fixture_admission("/unused", "sync", detector=detector) as report:
                self.assertEqual(report["status"], "DEFERRED")
                self.assertEqual(report["reason"], "LOCK_UNSUPPORTED")
        detector.assert_not_called()


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux flock required")
class AdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.detector = Mock(return_value=("STOPPED", ""))

    def test_both_roles(self):
        for role in ("sync", "emulator"):
            with fixture_admission(self.root, role, detector=self.detector) as report:
                self.assertEqual(report["status"], "ADMITTED")
                self.assertIs(report["write_authorized"], False)
                self.assertIs(report["coordination_verified"], False)

    def test_running(self):
        self.detector.return_value = ("RUNNING", "")
        with fixture_admission(self.root, "sync", detector=self.detector) as report:
            self.assertEqual(report["status"], "DEFERRED")
            self.assertEqual(report["reason"], "EMULATOR_RUNNING")

    def test_unknown(self):
        self.detector.return_value = ("UNKNOWN", "")
        with fixture_admission(self.root, "sync", detector=self.detector) as report:
            self.assertEqual(report["status"], "DEFERRED")
            self.assertEqual(report["reason"], "EMULATOR_STATE_UNKNOWN")

    def test_invalid_detector(self):
        for value in (None, ("STOPPED", None), ("INVALID", "")):
            self.detector.return_value = value
            with fixture_admission(self.root, "sync", detector=self.detector) as report:
                self.assertEqual(report["reason"], "EMULATOR_STATE_UNKNOWN")

    def test_detector_exception(self):
        self.detector.side_effect = RuntimeError("inspection failed")
        with fixture_admission(self.root, "sync", detector=self.detector) as report:
            self.assertEqual(report["reason"], "EMULATOR_STATE_UNKNOWN")

    def test_body_exception_releases(self):
        with self.assertRaisesRegex(RuntimeError, "body"):
            with fixture_admission(self.root, "sync", detector=self.detector):
                raise RuntimeError("body")
        with fixture_admission(self.root, "emulator", detector=self.detector) as report:
            self.assertEqual(report["status"], "ADMITTED")

    def test_detector_runs_under_lock(self):
        def inspect():
            other = Mock()
            with fixture_admission(self.root, "emulator", detector=other) as report:
                self.assertEqual(report["reason"], "LOCK_BUSY")
            other.assert_not_called()
            return "STOPPED", ""
        with fixture_admission(self.root, "sync", detector=inspect) as report:
            self.assertEqual(report["status"], "ADMITTED")

    def check_process_exclusion(self, holder, contender):
        import select
        child = subprocess.Popen(
            [sys.executable, "-B", "-u", "-c", CHILD, str(self.root), holder],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True)
        try:
            ready, _, _ = select.select([child.stdout], [], [], 10)
            self.assertTrue(ready)
            self.assertEqual(json.loads(child.stdout.readline())["status"], "ADMITTED")
            other = Mock()
            with fixture_admission(self.root, contender, detector=other) as report:
                self.assertEqual(report["status"], "DEFERRED")
                self.assertEqual(report["reason"], "LOCK_BUSY")
            other.assert_not_called()
            child.communicate(timeout=10)
            self.assertEqual(child.returncode, 0)
            with fixture_admission(self.root, contender, detector=self.detector) as report:
                self.assertEqual(report["status"], "ADMITTED")
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_emulator_excludes_sync(self):
        self.check_process_exclusion("emulator", "sync")

    def test_sync_excludes_emulator(self):
        self.check_process_exclusion("sync", "emulator")
