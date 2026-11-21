import tempfile
import unittest
from pathlib import Path

from preflight import check_exit_code, detect_retroarch, preflight


class ProcessDetectionTests(unittest.TestCase):
    def test_running_by_comm(self):
        with tempfile.TemporaryDirectory() as d:
            pid = Path(d) / "123"
            pid.mkdir()
            (pid / "comm").write_text("retroarch\n")
            (pid / "cmdline").write_bytes(b"/usr/bin/retroarch\\0")
            status, _ = detect_retroarch(Path(d), "linux")
            self.assertEqual(status, "RUNNING")

    def test_running_by_argv_zero(self):
        with tempfile.TemporaryDirectory() as d:
            pid = Path(d) / "123"
            pid.mkdir()
            (pid / "comm").write_text("steam-runtime\n")
            (pid / "cmdline").write_bytes(b"/usr/bin/retroarch\\0--verbose\\0")
            self.assertEqual(detect_retroarch(Path(d), "linux")[0], "RUNNING")

    def test_mentioned_only_in_arguments_is_not_running(self):
        with tempfile.TemporaryDirectory() as d:
            pid = Path(d) / "123"
            pid.mkdir()
            (pid / "comm").write_text("bash\n")
            (pid / "cmdline").write_bytes(b"/bin/bash\\0retroarch\\0")
            self.assertEqual(detect_retroarch(Path(d), "linux")[0], "STOPPED")

    def test_windows_unknown(self):
        self.assertEqual(detect_retroarch(Path("unused"), "win32")[0], "UNKNOWN")

    def test_unreadable_process_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "123").mkdir()
            self.assertEqual(detect_retroarch(Path(d), "linux")[0], "UNKNOWN")


class PreflightTests(unittest.TestCase):
    def test_missing_mount_fails_and_remote_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            config = {"schema_version": 1, "nas": {
                "mount": d, "expected_source": "//nas/Emulation",
                "remote_root": "Save"}, "games": [{
                    "id": "wario", "filename": "Wario", "local_dir": d,
                    "remote_dir": "gbc"}]}
            def fail_mount(mount, source):
                raise RuntimeError("NAS not mounted")
            with tempfile.TemporaryDirectory() as proc:
                checks = preflight(config, fail_mount, Path(proc), "linux")
            by_name = {c["name"]: c["status"] for c in checks}
            self.assertEqual(by_name["nas_mount"], "FAIL")
            self.assertEqual(by_name["remote:wario"], "SKIP")
            self.assertEqual(check_exit_code(checks), 2)

    def test_good_environment_warns_about_batocera(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Save" / "gbc").mkdir(parents=True)
            config = {"schema_version": 1, "nas": {
                "mount": d, "expected_source": "//nas/Emulation",
                "remote_root": "Save"}, "games": [{
                    "id": "wario", "filename": "Wario", "local_dir": d,
                    "remote_dir": "gbc"}]}
            with tempfile.TemporaryDirectory() as proc:
                checks = preflight(config, lambda mount, source: None,
                                   Path(proc), "linux")
            self.assertEqual(check_exit_code(checks), 0)
            self.assertEqual(checks[-1]["status"], "UNKNOWN")

    def test_bad_schema_fails(self):
        checks = preflight({"schema_version": 99}, lambda *_: None)
        self.assertEqual(check_exit_code(checks), 2)


if __name__ == "__main__":
    unittest.main()
