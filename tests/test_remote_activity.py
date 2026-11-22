import subprocess
import unittest
from types import SimpleNamespace

from remote_activity import detect_batocera_retroarch, parse_process_list


IDLE = """ 2031 openbox
 2036 emulationstatio
 2301 dbus-run-sessio
 2308 emulationstatio
"""
PLAYING = IDLE + " 3810 retroarch\n"


class RemoteActivityTests(unittest.TestCase):
    def test_idle_menu(self):
        self.assertEqual(parse_process_list(IDLE)[0], "STOPPED")

    def test_wario_running(self):
        status, detail = parse_process_list(PLAYING)
        self.assertEqual(status, "RUNNING")
        self.assertIn("3810", detail)

    def test_unrelated_zombie_does_not_hide_running_retroarch(self):
        listing = PLAYING + " 1429 uname <defunct>\\n"
        status, detail = parse_process_list(listing)
        self.assertEqual(status, "RUNNING")
        self.assertIn("3810", detail)

    def test_zombie_retroarch_is_not_running(self):
        self.assertEqual(
            parse_process_list(IDLE + " 1429 retroarch <defunct>\\n")[0],
            "STOPPED",
        )

    def test_unexpected_suffix_remains_unknown(self):
        self.assertEqual(
            parse_process_list(IDLE + " 1429 uname <unexpected>\\n")[0],
            "UNKNOWN",
        )

    def test_empty_response_is_unknown(self):
        self.assertEqual(parse_process_list("")[0], "UNKNOWN")

    def test_malformed_response_is_unknown(self):
        self.assertEqual(parse_process_list("permission denied")[0], "UNKNOWN")

    def test_process_mentioned_in_arguments_is_not_matched(self):
        self.assertEqual(parse_process_list(" 1 bash retroarch\n")[0], "UNKNOWN")

    def test_ssh_success(self):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0, stdout=PLAYING)
        self.assertEqual(detect_batocera_retroarch("192.168.1.75", runner=runner)[0], "RUNNING")
        command, kwargs = calls[0]
        self.assertIn("BatchMode=yes", command)
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertEqual(command[-2], "root@192.168.1.75")
        self.assertEqual(command[-1], "ps -eo pid=,comm=")
        self.assertLessEqual(kwargs["timeout"], 8)

    def test_ssh_failure_unknown(self):
        def runner(*args, **kwargs):
            return SimpleNamespace(returncode=255, stdout="")
        self.assertEqual(detect_batocera_retroarch("192.168.1.75", runner=runner)[0], "UNKNOWN")

    def test_ssh_timeout_unknown(self):
        def runner(*args, **kwargs):
            raise subprocess.TimeoutExpired("ssh", 8)
        self.assertEqual(detect_batocera_retroarch("192.168.1.75", runner=runner)[0], "UNKNOWN")

    def test_ssh_missing_unknown(self):
        def runner(*args, **kwargs):
            raise FileNotFoundError("ssh")
        self.assertEqual(detect_batocera_retroarch("192.168.1.75", runner=runner)[0], "UNKNOWN")

    def test_unsafe_host_rejected_before_running_ssh(self):
        def runner(*args, **kwargs):
            self.fail("SSH should not run")
        self.assertEqual(detect_batocera_retroarch("-oProxyCommand=evil", runner=runner)[0], "UNKNOWN")

    def test_unsafe_user_rejected(self):
        self.assertEqual(detect_batocera_retroarch("batocera", user="-bad")[0], "UNKNOWN")

    def test_invalid_timeout_rejected(self):
        self.assertEqual(detect_batocera_retroarch("batocera", timeout=0)[0], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
